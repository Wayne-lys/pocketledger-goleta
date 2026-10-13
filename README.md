# PocketLedger

PocketLedger 是一个仅用 Python 标准库实现的个人人民币支出账本。它通过命令行增加、列出和汇总支出，不需要安装第三方包或连接网络。

## 环境与启动

需要 Python 3.11 或更新版本。进入本项目目录，确认 `python3` 指向符合要求的解释器，即可直接运行，无需安装：

```sh
python3 --version
python3 -m pocketledger --db ./data/ledger.sqlite3 add --date 2026-10-13 --category 餐饮 --amount 23.50 --note 午餐
python3 -m pocketledger --db ./data/ledger.sqlite3 list
python3 -m pocketledger --db ./data/ledger.sqlite3 list --from-date 2026-10-01 --to-date 2026-10-31
python3 -m pocketledger --db ./data/ledger.sqlite3 summary
python3 -m pocketledger --db ./data/ledger.sqlite3 summary --category 餐饮
python3 -m pocketledger --db ./data/ledger.sqlite3 list --json
python3 -m pocketledger --db ./data/ledger.sqlite3 summary --category 餐饮 --json
```

首次运行时会自动创建数据库文件及所需的父目录。以后使用同一个 `--db` 路径，就会读取之前保存的记录；数据只保存在该本地 SQLite 文件中。`--db` 是全局参数，须放在 `add`、`list` 或 `summary` 前面。

## 输入与输出

- `add` 成功时输出新记录的正整数 ID。
- 日期必须严格使用 `YYYY-MM-DD`，并且是有效的日历日期。
- 分类会去除首尾空白，去除后不得为空。备注可省略。
- 金额必须是大于零的普通十进制数字，最多两位小数；不接受符号、空白、科学计数法、`NaN`、`Infinity` 或超过 SQLite 整数范围的分数。金额以整数分保存，显示时固定为两位小数。
- `list` 按日期、ID 升序输出，每行包括 ID、日期、分类、金额和备注。分类与备注采用带引号的形式，换行等特殊字符会转义；空结果显示“账本为空。”。可以用 `--from-date` 和 `--to-date` 筛选日期，两个端点都包含在范围内；日期必须有效，起始日期不能晚于结束日期。
- `summary` 输出汇总范围、记录条数和两位小数的支出总额。可以用 `--category` 筛选分类；分类会去除首尾空白，去除后不得为空。空结果显示 0 条和 0.00 元。
- `list --json` 输出一个 JSON 数组，每条记录的字段为 `id`、`date`、`category`、`amount_cents`、`note`。`summary --json` 输出包含 `count` 和 `total_cents` 的 JSON 对象；使用分类筛选时还包含 `category`。JSON 中金额始终使用整数分，不使用浮点数。
- 文本模式保持中文输出；`--json` 模式的标准输出只包含一个可由 Python `json.loads` 解析的 JSON 值。错误始终写入标准错误输出，并返回非零退出码。
- 输入、数据库或路径出错时，命令返回非零退出码，并把错误写入标准错误输出。

## 运行测试

在项目目录执行：

```sh
python3 -m unittest discover -s tests -v
```

