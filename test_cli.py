"""通过子进程检查命令行的输出和退出码。"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_cli(database: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """以当前 Python 解释器实际启动模块。"""

    return subprocess.run(
        [sys.executable, "-m", "pocketledger", "--db", str(database), *arguments],
        cwd=_PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class CliTests(unittest.TestCase):
    def test_empty_add_list_and_summary(self) -> None:
        with tempfile.TemporaryDirectory(dir=_PROJECT_ROOT) as directory:
            database = Path(directory) / "nested" / "ledger.sqlite3"
            empty_list = run_cli(database, "list")
            self.assertEqual(empty_list.returncode, 0)
            self.assertEqual(empty_list.stdout.strip(), "账本为空。")

            empty_summary = run_cli(database, "summary")
            self.assertEqual(empty_summary.returncode, 0)
            self.assertIn("记录条数：0 条", empty_summary.stdout)
            self.assertIn("支出总额：0.00 元", empty_summary.stdout)

            first = run_cli(
                database, "add", "--date", "2024-03-02", "--category", " 餐饮 ",
                "--amount", "0.29", "--note", "午餐",
            )
            second = run_cli(
                database, "add", "--date", "2024-03-01", "--category", "交通",
                "--amount", "0.71",
            )
            self.assertEqual((first.returncode, first.stdout.strip()), (0, "1"))
            self.assertEqual((second.returncode, second.stdout.strip()), (0, "2"))

            listing = run_cli(database, "list")
            self.assertEqual(listing.returncode, 0)
            lines = listing.stdout.splitlines()
            self.assertEqual(len(lines), 2)
            self.assertIn("ID：2 | 日期：2024-03-01", lines[0])
            self.assertIn("金额：0.71 元", lines[0])
            self.assertIn("备注：\"\"", lines[0])
            self.assertIn("ID：1 | 日期：2024-03-02", lines[1])
            self.assertIn("分类：\"餐饮\"", lines[1])
            self.assertIn("备注：\"午餐\"", lines[1])

            summary = run_cli(database, "summary")
            self.assertEqual(summary.returncode, 0)
            self.assertIn("记录条数：2 条", summary.stdout)
            self.assertIn("支出总额：1.00 元", summary.stdout)

    def test_invalid_input_has_error_exit_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory(dir=_PROJECT_ROOT) as directory:
            database = Path(directory) / "ledger.sqlite3"
            cases = (
                ("--date", "2023-02-29", "--category", "餐饮", "--amount", "1"),
                ("--date", "2024-01-01", "--category", "  ", "--amount", "1"),
                ("--date", "2024-01-01", "--category", "餐饮", "--amount", "1e2"),
            )
            for arguments in cases:
                with self.subTest(arguments=arguments):
                    result = run_cli(database, "add", *arguments)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("错误：", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(database.exists())

    def test_database_error_has_error_exit_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory(dir=_PROJECT_ROOT) as directory:
            result = run_cli(Path(directory), "summary")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("错误：", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_list_date_range_is_inclusive_and_reverse_range_fails_before_query(self) -> None:
        with tempfile.TemporaryDirectory(dir=_PROJECT_ROOT) as directory:
            database = Path(directory) / "ledger.sqlite3"
            for date, amount in (
                ("2024-01-01", "1.00"),
                ("2024-01-02", "2.00"),
                ("2024-01-03", "3.00"),
            ):
                result = run_cli(
                    database,
                    "add",
                    "--date",
                    date,
                    "--category",
                    "测试",
                    "--amount",
                    amount,
                )
                self.assertEqual(result.returncode, 0)

            included = run_cli(
                database,
                "list",
                "--from-date",
                "2024-01-02",
                "--to-date",
                "2024-01-02",
            )
            self.assertEqual(included.returncode, 0)
            self.assertIn("ID：2 | 日期：2024-01-02", included.stdout)
            self.assertNotIn("2024-01-01", included.stdout)
            self.assertNotIn("2024-01-03", included.stdout)

            invalid_date = run_cli(
                database, "list", "--from-date", "2024-02-30"
            )
            self.assertNotEqual(invalid_date.returncode, 0)
            self.assertEqual(invalid_date.stdout, "")
            self.assertIn("错误：", invalid_date.stderr)

            reversed_database = Path(directory) / "reversed" / "ledger.sqlite3"
            reversed_range = run_cli(
                reversed_database,
                "list",
                "--from-date",
                "2024-01-03",
                "--to-date",
                "2024-01-02",
            )
            self.assertNotEqual(reversed_range.returncode, 0)
            self.assertEqual(reversed_range.stdout, "")
            self.assertIn("日期范围错误", reversed_range.stderr)
            self.assertFalse(reversed_database.exists())

    def test_category_summary_text_empty_category_and_empty_result(self) -> None:
        with tempfile.TemporaryDirectory(dir=_PROJECT_ROOT) as directory:
            database = Path(directory) / "ledger.sqlite3"
            for category, amount in (("餐饮", "1.20"), ("餐饮", "0.30"), ("交通", "2.00")):
                result = run_cli(
                    database,
                    "add",
                    "--date",
                    "2024-01-01",
                    "--category",
                    category,
                    "--amount",
                    amount,
                )
                self.assertEqual(result.returncode, 0)

            filtered = run_cli(database, "summary", "--category", " 餐饮 ")
            self.assertEqual(filtered.returncode, 0)
            self.assertIn("汇总范围：分类“餐饮”", filtered.stdout)
            self.assertIn("记录条数：2 条", filtered.stdout)
            self.assertIn("支出总额：1.50 元", filtered.stdout)

            empty_result = run_cli(database, "summary", "--category", "住宿")
            self.assertEqual(empty_result.returncode, 0)
            self.assertIn("记录条数：0 条", empty_result.stdout)
            self.assertIn("支出总额：0.00 元", empty_result.stdout)

            empty_category = run_cli(database, "summary", "--category", "  ")
            self.assertNotEqual(empty_category.returncode, 0)
            self.assertEqual(empty_category.stdout, "")
            self.assertIn("错误：", empty_category.stderr)

    def test_json_list_and_summary_are_parseable(self) -> None:
        with tempfile.TemporaryDirectory(dir=_PROJECT_ROOT) as directory:
            database = Path(directory) / "ledger.sqlite3"
            first = run_cli(
                database,
                "add",
                "--date",
                "2024-01-02",
                "--category",
                "餐饮",
                "--amount",
                "1.20",
                "--note",
                "午餐",
            )
            second = run_cli(
                database,
                "add",
                "--date",
                "2024-01-01",
                "--category",
                "交通",
                "--amount",
                "0.30",
            )
            self.assertEqual((first.returncode, second.returncode), (0, 0))

            listing = run_cli(
                database,
                "list",
                "--from-date",
                "2024-01-02",
                "--json",
            )
            self.assertEqual(listing.returncode, 0)
            self.assertEqual(listing.stderr, "")
            self.assertEqual(
                json.loads(listing.stdout),
                [
                    {
                        "id": 1,
                        "date": "2024-01-02",
                        "category": "餐饮",
                        "amount_cents": 120,
                        "note": "午餐",
                    }
                ],
            )

            summary = run_cli(database, "summary", "--category", "餐饮", "--json")
            self.assertEqual(summary.returncode, 0)
            self.assertEqual(
                json.loads(summary.stdout),
                {"count": 1, "total_cents": 120, "category": "餐饮"},
            )

            empty = run_cli(database, "list", "--from-date", "2025-01-01", "--json")
            self.assertEqual(empty.returncode, 0)
            self.assertEqual(json.loads(empty.stdout), [])


if __name__ == "__main__":
    unittest.main()

