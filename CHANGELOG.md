# 更新日志

本文件记录项目的重要变更。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本采用语义化版本与 `vX.Y.Z-betaN` 预发布标签。

## [3.1.0-beta1] - 2026-06-20

### 新增（Added）
- **一对一倾听观察子系统（dev3.1）**：教师对**单个幼儿**按**健康/语言/社会/艺术/科学五大领域**做一对一倾听观察（路由 `/one-on-one-listening`，「教学管理」菜单新增入口）。
  - **领域级独立观察时间**：每领域各自观察年月 + 3 个工作日；提供「自动选取本领域工作日」与顶部「一键为所有领域按各自年月选取」（前三周各取一工作日、排除法定节假日、API 不可用降级）。
  - **视觉 AI 生成**：每领域 1 次视觉调用，返回该领域目标、3 张幼儿绘画图片描述（有字识别/无字描述）、各二级指标达成星级（1~3，未涉及默认 3 星）、约 200 字综合评价与支持策略；可逐领域生成或「生成全部领域」串行。
  - **二级指标目录**：迁移预置「小班·下学期」五大领域共 30 个二级指标（`indicator_catalog`，可按 `(grade, term, domain)` 扩展）。
  - **图片处理**：上传即统一为横版（EXIF 校正 + 竖版旋转 90°）；「一键导入 15 张」按文件名排序自动分配五领域（每领域 3 张）；入库前 Pillow 压缩 ≤ 1MB（MySQL BLOB 可插拔存储）。
  - **Word 导出（模板 `OneOnOneListeningSmallSecond.docx`，5 表）**：单幼儿合并（1 档）/ 单幼儿按领域（5 档 zip）/ 多幼儿批量按领域（5 档 zip，每档含所选幼儿）；指标按星级行打勾 `√`、中文宋体不乱码、绘画图片与日期/评价/策略就位。
  - **历史与编辑**：历史列表（年月/姓名筛选）、只读详情弹窗、单条重新导出、多选批量导出、删除（含图片）、载入历史到表单**编辑覆盖保存**；导出写 `export_records(listening_record_id)` 并审计 `export_listening`。
  - **提示词管理**：新增 `one_on_one_listening` 任务类型 Tab（多版本 + 回滚）。
- 新增数据表 5 张（`listening_record` / `listening_domain` / `listening_image` / `listening_indicator_result` / `indicator_catalog`），`export_records` 增列 `listening_record_id`，`prompt_template.task_type` 枚举增值；Alembic 迁移 `e3c0e63a65c4`、种子 `9ec29bdc3822`（首次启动自动增量应用）。

### 说明（Notes）
- 数据隔离与安全沿用既有约定：全部查询强制 `tenant_id`；视觉模型 API Key Fernet 加密入库、脱敏展示、不写日志。
- 全量自动化回归 **461 passed**；本子系统 UI 交互为本次 beta 的人工验收重点。

[3.1.0-beta1]: https://github.com/ywyz/kindergartenManager/releases/tag/v3.1.0-beta1

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
