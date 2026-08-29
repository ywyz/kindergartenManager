"""PyInstaller 入口脚本。"""

import multiprocessing
import sys


def _run_main_app() -> None:
    from app.main import main

    main()


def _run_bootstrap_admin_cli() -> None:
    import asyncio

    from app.jobs import bootstrap_admin

    asyncio.run(bootstrap_admin._main())


def _run_entrypoint(argv: list[str] | None = None) -> None:
    """入口分派：检测 init / reset-password 参数并路由到对应启动路径。"""

    args = argv if argv is not None else sys.argv
    if "--init" in args or "--reset-password" in args:
        _run_bootstrap_admin_cli()
    else:
        _run_main_app()


if __name__ == "__main__":
    # multiprocessing/PyInstaller 安全护栏：必须在任何子进程派生前、且作为
    # __main__ 的第一条语句调用。打包（frozen）后若缺失，被派生的子进程会重新
    # 执行本入口 → 反复启动服务器 → 进程指数爆炸（fork bomb），导致整机
    # CPU/内存耗尽卡死。非打包模式下该调用为无害的空操作。
    multiprocessing.freeze_support()
    _run_entrypoint()
