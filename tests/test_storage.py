"""检查数据库初始化、持久化、排序和汇总。"""

import tempfile
import unittest
from pathlib import Path

from pocketledger.storage import LedgerStore, StorageError
from pocketledger.validation import validate_expense


_PROJECT_ROOT = Path(__file__).resolve().parents[1]


class StorageTests(unittest.TestCase):
    def test_initialization_persistence_order_and_summary(self) -> None:
        with tempfile.TemporaryDirectory(dir=_PROJECT_ROOT) as directory:
            path = Path(directory) / "nested" / "ledger.sqlite3"
            store = LedgerStore(str(path))
            self.assertEqual(store.list_expenses(), [])
            self.assertTrue(path.is_file())
            self.assertEqual(store.summary().count, 0)
            self.assertEqual(store.summary().total_cents, 0)

            first_id = store.add(validate_expense("2024-03-02", "餐饮", "0.29"))
            second_id = store.add(validate_expense("2024-03-01", "交通", "0.71"))
            self.assertEqual((first_id, second_id), (1, 2))

            reopened = LedgerStore(str(path))
            self.assertEqual([record.id for record in reopened.list_expenses()], [2, 1])
            self.assertEqual(reopened.summary().count, 2)
            self.assertEqual(reopened.summary().total_cents, 100)

    def test_summary_uses_unbounded_python_integer(self) -> None:
        with tempfile.TemporaryDirectory(dir=_PROJECT_ROOT) as directory:
            store = LedgerStore(str(Path(directory) / "ledger.sqlite3"))
            expense = validate_expense("2024-01-01", "测试", "92233720368547758.07")
            store.add(expense)
            store.add(expense)
            self.assertEqual(store.summary().total_cents, 2 * (2**63 - 1))

    def test_unusable_database_path(self) -> None:
        with tempfile.TemporaryDirectory(dir=_PROJECT_ROOT) as directory:
            with self.assertRaises(StorageError):
                LedgerStore(directory).list_expenses()
            with self.assertRaises(StorageError):
                LedgerStore(":memory:").summary()

    def test_date_and_category_filters(self) -> None:
        with tempfile.TemporaryDirectory(dir=_PROJECT_ROOT) as directory:
            store = LedgerStore(str(Path(directory) / "ledger.sqlite3"))
            store.add(validate_expense("2024-01-01", "餐饮", "1.00"))
            store.add(validate_expense("2024-01-02", "交通", "2.00"))
            store.add(validate_expense("2024-01-03", "餐饮", "3.00"))

            records = store.list_expenses("2024-01-02", "2024-01-02")
            self.assertEqual([record.date for record in records], ["2024-01-02"])
            self.assertEqual(store.summary("餐饮").count, 2)
            self.assertEqual(store.summary("餐饮").total_cents, 400)
            self.assertEqual(store.summary("餐饮' OR 1=1 --").count, 0)


if __name__ == "__main__":
    unittest.main()
