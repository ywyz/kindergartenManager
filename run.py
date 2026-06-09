"""PyInstaller 入口脚本。

此文件作为 kindergartenManager.spec 的 Analysis 入口，
不能用 `python -m app.main` 方式启动，仅供 PyInstaller 构建使用。
"""
from app.main import main

if __name__ == "__main__":
    main()
