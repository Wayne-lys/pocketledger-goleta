"""使用用户指定的本地 SQLite 文件持久化支出。"""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .validation import ExpenseInput


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_date TEXT NOT NULL,
    category TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    note TEXT NOT NULL
)
"""


class StorageError(Exception):
    """表示数据库或其路径无法正常使用。"""


@dataclass(frozen=True, slots=True)
class ExpenseRecord:
    """从数据库读取的一条支出。"""

    id: int
    date: str
    category: str
    amount_cents: int
    note: str


@dataclass(frozen=True, slots=True)
class LedgerSummary:
    """账本的记录条数和支出总分数。"""

    count: int
    total_cents: int


class LedgerStore:
    """每次操作连接指定文件，并在文件不存在时创建数据表。"""

    def __init__(self, database_path: str) -> None:
        self.database_path = database_path

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = None
        try:
            if not self.database_path.strip():
                raise StorageError("数据库路径不能为空。")
            if self.database_path == ":memory:":
                raise StorageError("请指定本地 SQLite 文件路径。")

            path = Path(self.database_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(str(path))
            with connection:
                connection.execute(_CREATE_TABLE)
                yield connection
        except (OSError, sqlite3.Error, ValueError) as exc:
            raise StorageError(f"数据库操作失败：{exc}") from None
        finally:
            if connection is not None:
                connection.close()

    def add(self, expense: ExpenseInput) -> int:
        """写入一条支出，并返回数据库生成的正整数 ID。"""

        with self._connection() as connection:
            cursor = connection.execute(
                """INSERT INTO expenses (expense_date, category, amount_cents, note)
                   VALUES (?, ?, ?, ?)""",
                (expense.date, expense.category, expense.amount_cents, expense.note),
            )
            return cursor.lastrowid

    def list_expenses(
        self, from_date: str | None = None, to_date: str | None = None
    ) -> list[ExpenseRecord]:
        """按日期、ID 升序读取支出，可按包含边界的日期范围筛选。"""

        with self._connection() as connection:
            conditions: list[str] = []
            parameters: list[str] = []
            if from_date is not None:
                conditions.append("expense_date >= ?")
                parameters.append(from_date)
            if to_date is not None:
                conditions.append("expense_date <= ?")
                parameters.append(to_date)

            query = """SELECT id, expense_date, category, amount_cents, note
                       FROM expenses"""
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY expense_date ASC, id ASC"
            rows = connection.execute(query, parameters).fetchall()
            return [ExpenseRecord(*row) for row in rows]

    def summary(self, category: str | None = None) -> LedgerSummary:
        """按可选分类汇总，并用 Python 整数避免数据库整数求和溢出。"""

        with self._connection() as connection:
            query = "SELECT amount_cents FROM expenses"
            parameters: list[str] = []
            if category is not None:
                query += " WHERE category = ?"
                parameters.append(category)

            count = 0
            total_cents = 0
            for (amount_cents,) in connection.execute(query, parameters):
                count += 1
                total_cents += amount_cents
            return LedgerSummary(count=count, total_cents=total_cents)
