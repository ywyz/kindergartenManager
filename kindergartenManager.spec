# -*- mode: python ; coding: utf-8 -*-
# kindergartenManager.spec — PyInstaller 构建规格文件
#
# 构建命令：
#   pip install pyinstaller
#   pyinstaller kindergartenManager.spec
#
# 产物位于 dist/ 目录

import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

# ── NiceGUI：必须 collect_all 以包含所有静态资源（JS/CSS/图标） ──────────────
nicegui_datas, nicegui_binaries, nicegui_hiddenimports = collect_all("nicegui")

# ── 额外隐式导入 ─────────────────────────────────────────────────────────────
hidden_imports = [
    *nicegui_hiddenimports,
    # 数据库驱动
    "aiosqlite",
    "aiomysql",
    "pymysql",
    "pymysql.constants",
    "pymysql.constants.CLIENT",
    "pymysql.constants.COMMAND",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.mysql",
    "sqlalchemy.dialects.mysql.aiomysql",
    "sqlalchemy.dialects.mysql.pymysql",
    "sqlalchemy.ext.asyncio",
    # 认证与加密
    "argon2",
    "argon2._utils",
    "argon2.low_level",
    "cryptography.hazmat.primitives.ciphers.algorithms",
    "cryptography.hazmat.primitives.ciphers.modes",
    "cryptography.hazmat.primitives.kdf.pbkdf2",
    "jose",
    "jose.jwt",
    "jose.exceptions",
    # HTTP / 异步
    "httpx",
    "anyio",
    "anyio._backends._asyncio",
    "tenacity",
    # Word 导出
    "docx",
    "docx.oxml",
    "docx.oxml.ns",
    # 配置管理
    "pydantic_settings",
    "dotenv",
    # 调度器
    "apscheduler",
    "apscheduler.schedulers.asyncio",
    "apscheduler.triggers.cron",
    # 日志
    "pythonjsonlogger",
    # multipart（FastAPI 文件上传）
    "multipart",
    "python_multipart",
    # Alembic（迁移需要在运行时调用）
    "alembic",
    "alembic.command",
    "alembic.config",
    "alembic.runtime.migration",
    "alembic.runtime.environment",
    "alembic.script",
    "alembic.ddl",
    *collect_submodules("alembic"),
]

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=nicegui_binaries,
    datas=[
        # 应用模板（Word 导出模板）
        ("templates", "templates"),
        # Alembic 迁移脚本（运行时执行 upgrade head 需要）
        ("alembic", "alembic"),
        ("alembic.ini", "."),
        # NiceGUI 静态资源（JS/CSS/图标等）
        *nicegui_datas,
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除测试依赖，减小体积
        "pytest",
        "pytest_asyncio",
        "aiosqlite",  # 仅在测试中用，运行时不需要（SQLite 用 aiosqlite 在 hiddenimports 里）
    ],
    noarchive=False,
)

# 注意：excludes 中的 aiosqlite 会被 hiddenimports 覆盖（hiddenimports 优先级更高）
# 如果 SQLite 降级模式有问题，删除 excludes 中的 aiosqlite 条目

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="幼儿园教学管理系统",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,   # 保留控制台窗口以显示启动日志；后续版本可改为 False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可替换为 .ico 文件路径（Windows）或 .icns（macOS）
)
