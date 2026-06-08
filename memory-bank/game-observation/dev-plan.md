# 游戏观察子系统 — 分步开发计划

> 配套：[design.md](design.md)、[test-plan.md](test-plan.md)。
> 每个步骤含：目标 / 涉及文件 / 具体任务 / 验收点。每步完成后运行该步对应测试（见 test-plan.md），
> 全部通过再进入下一步；并在里程碑后更新 `memory-bank/architecture.md` 与 `progress.md`。
>
> 约定：DB 变更必须 `alembic revision --autogenerate -m "..."` 后人工核对再 `upgrade head`；
> service 层不直接发 HTTP；查询强制 `tenant_id`；Key 解密仅内存使用。
>
> **执行顺序（已确认）：先做阶段 0 界面重构，全量回归通过后再做阶段 A~I 游戏观察。**

---

## 阶段 0：界面重构（先行）

### 0.1 共享布局组件 app_shell
- 文件：`app/ui/components/app_shell.py`（新增）
- 任务：实现 `app_shell(user, active)` 上下文管理器：左侧 `ui.left_drawer` 分组菜单（教学管理/配置中心/账号中心）+ 顶栏（系统名、当前显示名、退出）；按角色显隐管理员菜单；`active` 高亮；`yield` 内容区。
- 验收：任意页面 `with app_shell(...)` 可渲染统一外壳。

### 0.2 首页仪表盘
- 文件：`app/ui/pages/home.py`
- 任务：套用 app_shell；欢迎信息（显示名，回退 username）+ 快捷入口卡片（每日活动计划/游戏观察记录）+ 当前班级信息（读 class_config）；删除占位文案与 `/date-test` 按钮。
- 验收：登录后进入仪表盘，卡片可跳转。

### 0.3 迁移既有页面到 app_shell
- 文件：`app/ui/pages/{settings,daily_plan,prompt_mgmt,user_admin}.py`
- 任务：删除各自 `ui.header()` 重复导航，改用 `with app_shell(...)` 包裹内容区；功能逻辑不动。
- 验收：4 个页面在新布局下功能与原先一致。

### 0.4 清理 date-test
- 文件：删除 `app/ui/pages/date_test.py`；`app/main.py` 移除 `import date_test`；确认无残留引用。
- 验收：`grep date-test` 无业务引用；应用启动正常。

### 0.5 回归
- 任务：`pytest tests/ -v` 全绿；手动验证各页面导航。
- 验收：既有用例不回归（注意是否有引用 date_test 的测试）。

> 里程碑 M-UI0：新布局上线，所有现有页面迁移完成、date-test 清理、回归通过。更新 architecture.md。

---

## 阶段 A：基础设施与依赖

### A1. 引入图片处理依赖
- 文件：`requirements.txt`
- 任务：新增 `Pillow>=10.0.0`；执行 `pip install -r requirements.txt`。
- 验收：`python -c "import PIL; print(PIL.__version__)"` 成功。

### A2. 配置项扩展
- 文件：`app/core/config.py`、`.env.example`
- 任务：新增 `IMAGE_STORAGE_BACKEND`（默认 `mysql_blob`）、`IMAGE_MAX_BYTES`（默认 1048576）。
- 验收：`settings.IMAGE_STORAGE_BACKEND == "mysql_blob"`。

---

## 阶段 B：数据模型与迁移

### B1. `ai_api_key` 增加 key_type
- 文件：`app/core/models/ai_key.py`，迁移 `alembic/versions/*_add_key_type_to_ai_api_key.py`
- 任务：新增 `key_type` ENUM(`text`,`vision`) `server_default='text'`；存量数据回填 `text`。
- 验收：迁移 upgrade/downgrade 正常；旧记录 key_type=text。

### B2. `user` 增加 display_name
- 文件：`app/core/models/user.py`，迁移 `*_add_display_name_to_user.py`
- 任务：新增 `display_name` VARCHAR(64) NULL。
- 验收：迁移成功；模型可读写该字段。

### B3. 新建 `game_observation` 表
- 文件：`app/core/models/game_observation.py`，迁移 `*_add_game_observation_table.py`
- 任务：按 design.md §4.1 建模（含隔离字段与时间戳）；在 `app/core/models/__init__.py` 导入以便 autogenerate。
- 验收：迁移成功，字段齐全。

### B4. 新建 `game_observation_image` 表
- 文件：`app/core/models/game_observation_image.py`，迁移 `*_add_game_observation_image_table.py`
- 任务：按 design.md §4.2 建模，`blob_content` 用 `LargeBinary().with_variant(LONGBLOB, "mysql")`。
- 验收：迁移成功；可存取二进制。

### B5. 新建 `invite_code` 表
- 文件：`app/core/models/invite_code.py`，迁移 `*_add_invite_code_table.py`
- 任务：按 design.md §4.5 建模，`code` 唯一索引。
- 验收：迁移成功；唯一约束生效。

### B6. 扩展 prompt_task_type 枚举
- 文件：`app/core/models/prompt_template.py`，迁移 `*_add_game_observation_task_type.py`
- 任务：Enum 增加 `game_observation`（MySQL `ALTER ... MODIFY`，参照既有 `e2a3f1b8c9d0`）。
- 验收：可保存 `task_type='game_observation'` 的提示词。

> 里程碑 M-DB：`alembic upgrade head` 全绿，更新 architecture.md 表清单。

---

## 阶段 C：图片处理与存储抽象

### C1. 图片压缩
- 文件：`app/integration/image_processing.py`
- 任务：`compress_image(data: bytes, max_bytes=settings.IMAGE_MAX_BYTES) -> CompressedImage(bytes, mime, width, height)`；
  策略：超阈值则等比缩放 + 逐级降 JPEG 质量；非法图片抛业务异常。
- 验收：>1MB 输入压缩后 ≤1MB；返回正确 mime/尺寸。

### C2. 存储后端抽象
- 文件：`app/integration/image_storage/base.py`、`blob_backend.py`、`__init__.py`
- 任务：定义 `ImageStorageBackend`（`put`/`get`）；实现 `BlobImageStorage`（写入/读取 `game_observation_image.blob_content`）；
  `get_storage_backend(settings)` 工厂；预留 s3/webdav 占位注释。
- 验收：blob 后端可 put/get 同一二进制。

---

## 阶段 D：仓库层

### D1. 观察记录仓库
- 文件：`app/repository/observation_repository.py`
- 任务：`save_observation(...)`（新增，返回带 id）、`get_observation_by_id`（带 tenant_id 过滤）、
  `list_observations(...)`（分页 + 日期/班级过滤）、`update_observation(...)`。
- 验收：CRUD 与 tenant 隔离正确。

### D2. 图片仓库
- 文件：`app/repository/observation_image_repository.py`
- 任务：`add_image`、`list_images_by_observation`（按 image_index 升序）、`get_image`（带隔离）、`delete_images_by_observation`。
- 验收：可存取多图并有序返回。

### D3. AI Key 仓库支持 key_type
- 文件：`app/repository/ai_key_repository.py`
- 任务：`save_ai_key(..., key_type='text')`、`get_active_ai_key(..., key_type='text')` 增参；deactivate 时按 key_type 限定。
- 验收：text/vision 两类独立 active 记录互不影响。

### D4. 邀请码仓库
- 文件：`app/repository/invite_code_repository.py`
- 任务：`create_code`、`get_active_by_code`、`list_codes`、`set_code_active`。
- 验收：停用后 `get_active_by_code` 返回 None。

### D5. 用户仓库扩展
- 文件：`app/repository/user_repository.py`
- 任务：`create_pending_user(...)`（is_active=False）、`update_display_name(...)`；用户名唯一校验（同 tenant）。
- 验收：注册创建待审核用户；显示名可更新。

---

## 阶段 E：AI 视觉客户端

### E1. 视觉调用基座
- 文件：`app/integration/ai_client/vision_base.py`
- 任务：`call_ai_vision(messages, api_base_url, api_key, model_name, *, _client)`；
  多模态消息体；超时 60s；tenacity 重试 3 次；HTTP 错误提取响应体；返回解析后 JSON dict。
- 验收：mock 返回 JSON 时解析成功；HTTP 4xx 抛 `AiCallError`。

### E2. 观察生成客户端
- 文件：`app/integration/ai_client/observation_client.py`
- 任务：`generate_observation(images: list[bytes], context: dict, ..., system_prompt=None) -> dict`；
  将图片转 base64 data-url；内置 `DEFAULT_OBSERVATION_PROMPT`（4 字段 JSON + 纯文本格式约束）；
  缺字段降级/抛 `AiParseError`。
- 验收：mock 返回 4 字段 → 正确映射；空图片列表抛异常。

---

## 阶段 F：服务层

### F1. 观察生成服务
- 文件：`app/service/observation_service.py`
- 任务：`generate_observation_content(session, tenant_id, user_id, images, context)`：
  取 `key_type='vision'` 的激活 Key（无则 `ConfigError`）→ 查 `game_observation` 提示词激活版本 →
  逐图 `compress_image` → `generate_observation` → `log_audit("ai_observation")` → 返回 4 字段 + 压缩后图片。
- 验收：未配置视觉 Key 抛 ConfigError；正常返回结构化结果。

### F2. 观察持久化服务（编排存储）
- 文件：`app/service/observation_service.py`（同文件内）
- 任务：`save_observation_with_images(session, ..., result, compressed_images)`：写 `game_observation` +
  逐图经存储后端写 `game_observation_image`；事务一致。
- 验收：保存后可按 id 取回记录 + 有序图片。

### F3. 注册与资料服务
- 文件：`app/service/auth_service.py`
- 任务：`register_user(session, invite_code, username, password, display_name)`（校验邀请码→tenant→唯一性→
  Argon2→创建待审核用户→`log_audit("register")`）；`update_profile_display_name(...)`；
  `approve_user(...)`（复用 set_active，`log_audit("approve_user")`）。
- 验收：无效邀请码抛业务异常；有效则创建 is_active=False。

### F4. 邀请码服务
- 文件：`app/service/invite_service.py`
- 任务：`generate_invite_code(session, tenant_id, created_by, note)`（随机 code）、`list/toggle`。
- 验收：仅 sys_admin 调用路径；code 随机唯一。

> 里程碑 M-CORE：阶段 C~F 单测全绿。

---

## 阶段 G：Word 导出

### G1. 观察记录导出器
- 文件：`app/integration/word_export/observation_exporter.py`
- 任务：`export_observation(observation, images: list[bytes]) -> bytes`：
  打开 `templates/ObservationRecord.docx`；替换标题 run 的 `xx`→大环境；按 §3 映射写入各单元格（先清空示例段落）；
  在 R5 右格文字下方追加段落横向并排插入图片；统一宋体 + `w:eastAsia`；模板缺失时降级从零构表。
- 验收：导出 docx 可打开；字段就位；图片在观察记录格内并排；中文不乱码。

### G2. 导出记录复用
- 文件：`app/repository/export_repository.py`、（可选）`app/core/models/export_record.py`
- 任务：导出后写 `export_records`；为区分来源，新增可空列 `observation_id`（迁移）或复用 `daily_plan_id=None`+`file_name` 约定（二选一，推荐加 `observation_id` 列更清晰）。
- 验收：导出生成记录，历史可查。

---

## 阶段 H：UI 页面

> 所有新增页面统一使用 `app/ui/components/app_shell.py`（阶段 0 已实现）。

### H1. 设置页 — 视觉模型配置
- 文件：`app/ui/pages/settings.py`
- 任务：在 AI 配置区拆分「文本模型 / 视觉模型」两块，各自保存（`key_type`），脱敏展示，验证连接。
- 验收：可分别保存并回显两类配置。

### H2. 游戏观察页
- 文件：`app/ui/pages/game_observation.py`（新增），`app/main.py`（如需注册）
- 任务：
  - 顶部：班级/年龄段只读展示（取 class_config）。
  - 表单：日期、起止时间、大环境(户外/室内/公共 下拉)、游戏区域、成人数目、儿童数目、幼儿姓名、幼儿年龄、观察者(默认显示名可改)。
  - 图片：`ui.upload` 1~3 张，前端校验数量/类型，预览。
  - 「生成观察记录」按钮 → 调 `observation_service` → 回填 4 段，可编辑。
  - 「保存」→ 持久化；「导出 Word」→ `export_observation` + `ui.download` + 写导出记录。
  - 异常按既有模式展示 `e.message`。
- 验收：完整闭环可用。

### H3. 观察历史（最简）
- 文件：`app/ui/pages/game_observation.py`（同页或子区块）
- 任务：列表查询本人观察记录，支持查看详情与重新导出。
- 验收：历史可查、可重新导出。

### H4. 提示词管理新增 Tab
- 文件：`app/ui/pages/prompt_mgmt.py`
- 任务：新增 `game_observation` Tab（编辑/保存/历史/回滚），与既有 7 个一致。
- 验收：可维护并回滚版本。

### H5. 注册页
- 文件：`app/ui/pages/register.py`（新增），`app/auth/middleware.py`（`/register` 加白名单），`app/ui/pages/login.py`（加注册入口）
- 任务：注册表单 → `register_user` → 成功提示等待审核。
- 验收：无效邀请码报错；有效则提示待审核。

### H6. 个人资料页
- 文件：`app/ui/pages/profile.py`（新增），`app/ui/pages/home.py`（加导航）
- 任务：编辑显示名、修改密码。
- 验收：显示名保存后，观察页观察者默认值随之更新。

### H7. 账号管理页 — 邀请码 + 待审核
- 文件：`app/ui/pages/user_admin.py`
- 任务：邀请码区块（列表/生成/启停）；用户列表新增「待审核」筛选与「启用」操作。
- 验收：sys_admin 可生成邀请码、审核启用用户。

### H8. 首页导航
- 文件：`app/ui/pages/home.py`
- 任务：新增「游戏观察」「个人资料」按钮。
- 验收：跳转正确。

> 里程碑 M-UI：端到端手动联调通过（含图片上传→生成→导出→历史）。

---

## 阶段 I：收尾
- I1. 审计接入核对（ai_observation / export_observation / register / approve_user / invite_code_create）。
- I2. 更新 `memory-bank/architecture.md`（新表、新模块、路由、已知问题）与 `progress.md`。
- I3. 全量回归 `pytest tests/ -v`，确保既有用例不回归。
- I4. README/文档同步（新增子系统简介与使用说明）。

---

## 文件清单速览（新增）
```
app/ui/components/app_shell.py        # 阶段0 共享布局
app/core/models/game_observation.py
app/core/models/game_observation_image.py
app/core/models/invite_code.py
app/integration/image_processing.py
app/integration/image_storage/{__init__,base,blob_backend}.py
app/integration/ai_client/vision_base.py
app/integration/ai_client/observation_client.py
app/repository/observation_repository.py
app/repository/observation_image_repository.py
app/repository/invite_code_repository.py
app/service/observation_service.py
app/service/invite_service.py
app/integration/word_export/observation_exporter.py
app/ui/pages/game_observation.py
app/ui/pages/register.py
app/ui/pages/profile.py
alembic/versions/*  (6+ 迁移)
tests/*  (见 test-plan.md)
```
修改：`requirements.txt`、`app/core/config.py`、`.env.example`、`app/core/models/__init__.py`、
`app/core/models/ai_key.py`、`app/core/models/user.py`、`app/core/models/prompt_template.py`、
`app/repository/{ai_key_repository,user_repository,export_repository}.py`、`app/service/auth_service.py`、
`app/ui/pages/{settings,prompt_mgmt,user_admin,login,home}.py`、`app/auth/middleware.py`、`app/main.py`。
