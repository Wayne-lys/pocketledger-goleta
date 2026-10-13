"""解析命令行参数，并输出支出记录或错误信息。"""

import argparse
import json
import sys

from .storage import LedgerStore, StorageError
from .validation import (
    ValidationError,
    validate_category,
    validate_date,
    validate_expense,
)


def _format_yuan(cents: int) -> str:
    """将整数分显示为固定两位小数的元。"""

    return f"{cents // 100}.{cents % 100:02d}"


def _build_parser() -> argparse.ArgumentParser:
    """构建仅包含账本所需三个命令的参数解析器。"""

    parser = argparse.ArgumentParser(description="记录本地人民币支出。")
    parser.add_argument("--db", required=True, metavar="路径", help="本地 SQLite 文件路径")
    commands = parser.add_subparsers(dest="command", required=True)

    add_parser = commands.add_parser("add", help="增加一条支出")
    add_parser.add_argument("--date", required=True, metavar="YYYY-MM-DD", help="支出日期")
    add_parser.add_argument("--category", required=True, metavar="分类", help="支出分类")
    add_parser.add_argument("--amount", required=True, metavar="金额", help="人民币金额")
    add_parser.add_argument("--note", default="", metavar="备注", help="可选备注")

    list_parser = commands.add_parser("list", help="按日期和 ID 升序列出全部支出")
    list_parser.add_argument("--from-date", metavar="YYYY-MM-DD", help="包含此日期")
    list_parser.add_argument("--to-date", metavar="YYYY-MM-DD", help="包含此日期")
    list_parser.add_argument("--json", action="store_true", help="以 JSON 输出")

    summary_parser = commands.add_parser("summary", help="显示记录条数和支出总额")
    summary_parser.add_argument("--category", metavar="分类", help="只汇总此分类")
    summary_parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    return parser


def main(argv: list[str] | None = None) -> int:
    """执行命令，正常返回零，用户或数据库错误返回非零。"""

    args = _build_parser().parse_args(argv)
    store = LedgerStore(args.db)

    try:
        if args.command == "add":
            expense = validate_expense(
                args.date, args.category, args.amount, args.note
            )
            print(store.add(expense))
        elif args.command == "list":
            from_date = (
                validate_date(args.from_date) if args.from_date is not None else None
            )
            to_date = (
                validate_date(args.to_date) if args.to_date is not None else None
            )
            if from_date is not None and to_date is not None and from_date > to_date:
                raise ValidationError("日期范围错误：起始日期不能晚于结束日期。")

            expenses = store.list_expenses(from_date=from_date, to_date=to_date)
            if args.json:
                payload = [
                    {
                        "id": expense.id,
                        "date": expense.date,
                        "category": expense.category,
                        "amount_cents": expense.amount_cents,
                        "note": expense.note,
                    }
                    for expense in expenses
                ]
                print(json.dumps(payload, ensure_ascii=False))
            else:
                if not expenses:
                    print("账本为空。")
                for expense in expenses:
                    category = json.dumps(expense.category, ensure_ascii=False)
                    note = json.dumps(expense.note, ensure_ascii=False)
                    print(
                        f"ID：{expense.id} | 日期：{expense.date} | "
                        f"分类：{category} | 金额：{_format_yuan(expense.amount_cents)} 元 | "
                        f"备注：{note}"
                    )
        elif args.command == "summary":
            category = (
                validate_category(args.category)
                if args.category is not None
                else None
            )
            summary = store.summary(category=category)
            if args.json:
                payload: dict[str, object] = {
                    "count": summary.count,
                    "total_cents": summary.total_cents,
                }
                if category is not None:
                    payload["category"] = category
                print(json.dumps(payload, ensure_ascii=False))
            else:
                scope = f"分类“{category}”" if category is not None else "全部分类"
                print(f"汇总范围：{scope}")
                print(f"记录条数：{summary.count} 条")
                print(f"支出总额：{_format_yuan(summary.total_cents)} 元")
    except (ValidationError, StorageError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 0

