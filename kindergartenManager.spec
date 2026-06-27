# -*- mode: python ; coding: utf-8 -*-
# kindergartenManager.spec — PyInstaller 构建规格文件
#
# 产物：dist/KindergartenManager/（onedir 目录，适合安装包和 systemd 部署）
#
# 构建命令：
#   pip install pyinstaller
#   pyinstaller kindergartenManager.spec
#
# 构建后目录：dist/KindergartenManager/
#   Windows：dist\KindergartenManager\KindergartenManager.exe
#   Linux：  dist/KindergartenManager/KindergartenManager

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
    # Alembic（启动时同步迁移）
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
        # Word 导出模板
        ("templates", "templates"),
        # Alembic 迁移脚本（startup.run_startup_migrations 运行时调用）
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
        "pytest",
        "pytest_asyncio",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

# ── onedir 模式：EXE 不含数据，由 COLLECT 聚合 ───────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,          # 数据/二进制由 COLLECT 统一放置
    name="KindergartenManager",     # ASCII 名称：规避 systemd/AV/CI 的 Unicode 路径问题
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                      # 禁用 UPX：避免压缩 DLL 损坏导致打包版启动挂起/崩溃
    upx_exclude=[],
    console=True,                   # beta 保留控制台，便于排错
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                      # 可替换为 .ico（Windows）或 .icns（macOS）
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,                      # 同上：禁用 UPX 压缩
    upx_exclude=[],
    name="KindergartenManager",     # dist/KindergartenManager/ 目录名
)
