# 更新日志

本文件记录项目的重要变更。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本采用语义化版本与 `vX.Y.Z-betaN` 预发布标签。

## [3.0.1-beta3] - 2026-06-19

### 修复（Fixed）
- **Windows 安装包安装后整机卡死**：定位为打包/运行层问题并系统性加固。
  - 新增 `app/core/paths.py` 的 `app_data_dir()`，统一将运行期文件写入「用户可写数据目录」
    （Windows `%LOCALAPPDATA%\KindergartenManager`、macOS `Application Support`、Linux
    `~/.local/share`）。修复打包版把 SQLite、密钥、`.env`、安装标记写入 `Program Files`
    只读目录导致的反复写失败（涉及 `database.py`、`config.py`、`startup.py`、`env_writer.py`、
    `setup_state.py` 共 5 处）。
  - 在 `run.py` 与 `app/main.py` 入口增加 `multiprocessing.freeze_support()`，修复 PyInstaller
    冻结后子进程重复执行入口造成的进程指数爆炸（fork-bomb），其典型表现即整机 CPU/内存耗尽卡死。
  - 打包桌面版 `ui.run` 监听地址由 `0.0.0.0` 改为 `127.0.0.1`（开发 / Docker / 服务器仍用
    `0.0.0.0`），规避 Windows 防火墙弹窗与「页面打不开」的假死观感。
  - PyInstaller 规格（`kindergartenManager.spec`）禁用 UPX 压缩，避免压缩 DLL 损坏导致启动挂起。
- **明文记录密码告警（CodeQL `py/clear-text-logging`）**：`app/jobs/bootstrap_admin.py` 的初始化/
  重置密码 CLI 不再直接打印「接收明文密码参数的函数」的返回值，改为按状态前缀输出固定文案，
  消除告警（相关函数的返回值与行为保持不变，测试不受影响）。

### 安全（Security）
- 提升依赖安全下限以修复 Dependabot 告警：`cryptography>=44.0.1`，并显式声明传递依赖安全下限
  `aiohttp`、`python-multipart`、`starlette`、`lxml`、`urllib3`、`idna`（构建时仍解析到各自最新版本）。

### 说明（Notes）
- 若安装后仍观察到整机卡死，请在 Windows 任务管理器确认 `KindergartenManager.exe` 进程数是否暴涨
  （fork-bomb，本次已修），或 `MsMpEng.exe`(Windows Defender) 是否占满 CPU（未签名安装包被杀软扫描所致，
  建议为安装目录添加杀软排除项；根治需代码签名证书）。

[3.0.1-beta3]: https://github.com/ywyz/kindergartenManager/releases/tag/v3.0.1-beta3
