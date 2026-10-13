"""命令行入口。"""import sysif sys.version_info < (3, 11):    print("错误：PocketLedger 需要 Python 3.11 或更新版本。", file=sys.stderr)    raise SystemExit(2)from .cli import mainraise SystemExit(main())

