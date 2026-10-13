"""校验支出输入，并将人民币金额精确转换为整数分。"""

import re
from dataclasses import dataclass
from datetime import date as calendar_date


_DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_AMOUNT_PATTERN = re.compile(r"[0-9]+(?:\.[0-9]{1,2})?")
_MAX_CENTS = 2**63 - 1


class ValidationError(ValueError):
    """表示用户输入不符合支出记录的要求。"""


@dataclass(frozen=True, slots=True)
class ExpenseInput:
    """已校验、可写入数据库的一条支出。"""

    date: str
    category: str
    amount_cents: int
    note: str


def validate_date(value: str) -> str:
    """要求日期严格使用有效的 YYYY-MM-DD 日历日期。"""

    if _DATE_PATTERN.fullmatch(value) is None:
        raise ValidationError("日期必须是有效的 YYYY-MM-DD 日历日期。")
    try:
        calendar_date.fromisoformat(value)
    except ValueError:
        raise ValidationError("日期必须是有效的 YYYY-MM-DD 日历日期。") from None
    return value


def validate_category(value: str) -> str:
    """去除分类首尾空白，并拒绝空分类。"""

    category = value.strip()
    if not category:
        raise ValidationError("分类去除首尾空白后不能为空。")
    return category


def validate_amount(value: str) -> int:
    """只接受普通十进制正数，返回精确的整数分。"""

    if _AMOUNT_PATTERN.fullmatch(value) is None:
        raise ValidationError("金额必须是正数，且最多保留两位小数。")

    whole, separator, fraction = value.partition(".")
    whole = whole.lstrip("0") or "0"
    if len(whole) > 17:
        raise ValidationError("金额超出 SQLite 整数分的可存储范围。")

    cents = int(whole) * 100
    if separator:
        cents += int(fraction.ljust(2, "0"))

    if cents == 0:
        raise ValidationError("金额必须大于零。")
    if cents > _MAX_CENTS:
        raise ValidationError("金额超出 SQLite 整数分的可存储范围。")
    return cents


def validate_expense(
    date: str, category: str, amount: str, note: str = ""
) -> ExpenseInput:
    """汇总校验一条支出，并保留原样备注。"""

    return ExpenseInput(
        date=validate_date(date),
        category=validate_category(category),
        amount_cents=validate_amount(amount),
        note=note,
    )
