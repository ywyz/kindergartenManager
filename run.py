"""PyInstaller 入口脚本。

此文件作为 kindergartenManager.spec 的 Analysis 入口，
不能用 `python -m app.main` 方式启动，仅供 PyInstaller 构建使用。
"""
import multiprocessing

from app.main import main

if __name__ == "__main__":
    # multiprocessing/PyInstaller 安全护栏：必须在任何子进程派生前、且作为
    # __main__ 的第一条语句调用。打包（frozen）后若缺失，被派生的子进程会重新
    # 执行本入口 → 反复启动服务器 → 进程指数爆炸（fork bomb），导致整机
    # CPU/内存耗尽卡死。非打包模式下该调用为无害的空操作。
    multiprocessing.freeze_support()
    main()
