"""检查日期、分类和整数分校验。"""

import unittest

from pocketledger.validation import ValidationError, validate_amount, validate_expense


class ValidationTests(unittest.TestCase):
    def test_valid_expense(self) -> None:
        expense = validate_expense("2024-02-29", "  餐饮  ", "000.29", "午餐")
        self.assertEqual(expense.date, "2024-02-29")
        self.assertEqual(expense.category, "餐饮")
        self.assertEqual(expense.amount_cents, 29)
        self.assertEqual(expense.note, "午餐")

    def test_invalid_dates_and_category(self) -> None:
        for value in ("2023-02-29", "2024-13-01", "2024-2-9", "20240229", "2024-04-31"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_expense(value, "餐饮", "1")
        with self.assertRaises(ValidationError):
            validate_expense("2024-02-29", " \t ", "1")

    def test_exact_amounts_and_sqlite_limit(self) -> None:
        for value, cents in (
            ("0.01", 1),
            ("0.29", 29),
            ("1", 100),
            ("1.2", 120),
            ("92233720368547758.07", 2**63 - 1),
        ):
            with self.subTest(value=value):
                self.assertEqual(validate_amount(value), cents)

    def test_invalid_amounts(self) -> None:
        for value in (
            "0", "0.00", "-1", "+1", "1.234", "1e2", "NaN", "Infinity",
            ".5", "1.", " 1", "1 ", "92233720368547758.08", "9" * 5000,
        ):
            with self.subTest(value=value[:30]), self.assertRaises(ValidationError):
                validate_amount(value)


if __name__ == "__main__":
    unittest.main()
