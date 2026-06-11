# 游戏观察子系统 — 开发与测试进度

> 配套：[design.md](design.md)、[dev-plan.md](dev-plan.md)、[test-plan.md](test-plan.md)

---

## 开发日志

### 2026-06-09 — 阶段 0：界面重构（M-UI0）

#### 完成内容

**TDD 流程**：先写测试（红）→ 再实现（绿）

**新增文件**
- `app/ui/components/__init__.py` — 组件包初始化
- `app/ui/components/app_shell.py` — 共享布局组件
  - `get_menu_items(role, active=None) -> list[dict]`：纯函数，角色过滤+高亮标记
  - `get_display_name(user) -> str`：纯函数，display_name 有值则用，否则回退 username
  - `app_shell(user, active)` — async context manager，用于新页面（如 home.py）
  - `render_shell(user, active)` — async 函数，用于迁移既有页面（无需重新缩进）
- `tests/test_app_shell_menu.py` — 新建单测（10 个用例）

**修改文件**
- `app/ui/pages/home.py` — 重写为仪表盘（欢迎信息 + 快捷卡片 + 班级信息）
- `app/ui/pages/settings.py` — 替换导航头，使用 `render_shell`
- `app/ui/pages/daily_plan.py` — 替换导航头，使用 `render_shell`
- `app/ui/pages/prompt_mgmt.py` — 替换导航头，使用 `render_shell`
- `app/ui/pages/user_admin.py` — 替换导航头，使用 `render_shell`
- `app/main.py` — 移除 `date_test` import

**删除文件**
- `app/ui/pages/date_test.py`

#### 菜单分组设计

| 分组 | 菜单项 | 角色限制 |
|------|--------|----------|
| 教学管理 | 每日活动计划、游戏观察记录 | 所有角色 |
| 配置中心 | 学期班级配置、AI 提示词管理 | 所有角色 |
| 账号中心 | 个人资料、账号管理 | 账号管理仅 sys_admin |

#### 自动测试结果

**test_app_shell_menu.py（新增，运行两次）**

| 时间 | 状态 |
|------|------|
| 实现前（红） | ERROR — `ModuleNotFoundError: No module named 'app.ui.components.app_shell'` |
| 实现后（绿） | **10/10 passed** |

**全量回归（pytest tests/ -v）**

| 指标 | 值 |
|------|----|
| 总用例数 | **261 passed** |
| 失败 | 0 |
| 耗时 | 18.44s |
| 原有用例 | 228（无回归） |
| 新增用例 | 10（test_app_shell_menu.py）+ 23（原有数量统计调整） |

#### 手动测试结果 ✅（2026-06-09 验证通过）

| 测试项 | 结果 |
|--------|------|
| 登录后进入仪表盘：欢迎信息正确、班级信息展示、快捷卡片可跳转 | ✅ 通过 |
| 左侧菜单：分组正确（教学管理/配置中心/账号中心）、当前页高亮、退出可用 | ✅ 通过 |
| settings / daily-plan / prompts / user-admin 在新布局下功能与原先一致 | ✅ 通过 |
| 访问 `/date-test` 返回 404 或被路由守卫处理 | ✅ 通过 |

**里程碑 M-UI0：✅ 已完成**

---

## 待办（后续阶段）

### 阶段 A：基础设施 ✅（2026-06-09）

| 步骤 | 内容 | 状态 |
|------|------|------|
| A.T | 写测试 `tests/test_config_image_settings.py`（3 用例）→ 先红 | ✅ |
| A.1 | `app/core/config.py` 新增 `IMAGE_STORAGE_BACKEND`（默认 `mysql_blob`）、`IMAGE_MAX_BYTES`（默认 1048576） | ✅ |
| A.2 | `requirements.txt` 新增 `Pillow>=10.0.0`；`pip install` 到 `.venv` | ✅ |
| 测试 | `pytest tests/test_config_image_settings.py -v` → **3/3 passed** | ✅ |
| 回归 | `pytest tests/ -v` → **264 passed, 0 failed** | ✅ |

### 阶段 B：数据模型（2026-06-09）

| 步骤 | 内容 | 状态 |
|------|------|------|
| B.T | 写测试 `tests/test_migrations_smoke.py`（9 用例）→ 先红 | ✅ |
| B.1 | `app/core/models/ai_key.py` 新增 `key_type` ENUM(text/vision)，server_default='text' | ✅ |
| B.2 | `app/core/models/user.py` 新增 `display_name` VARCHAR(64) NULL | ✅ |
| B.3 | 新建 `app/core/models/game_observation.py`（17 字段） | ✅ |
| B.4 | 新建 `app/core/models/game_observation_image.py`（LargeBinary + LONGBLOB variant） | ✅ |
| B.5 | 新建 `app/core/models/invite_code.py`（code UNIQUE 约束） | ✅ |
| B.6 | `app/core/models/prompt_template.py` Enum 增加 `game_observation` | ✅ |
| - | `app/core/models/__init__.py` 新增 3 个 model 导入 | ✅ |
| - | `app/core/exceptions.py` 新增 `AppError` | ✅ |
| 测试 | 9/9 passed | ✅ |
| Alembic 迁移 | 2 个迁移脚本已执行：`54c20d37a461`（新表+新列）、`ff6b88b2ee1e`（Enum 扩展）| ✅ |

**手动验证（MySQL）✅（2026-06-09）**

| 验证项 | 结果 |
|--------|------|
| `ai_api_key.key_type` ENUM('text','vision') DEFAULT text | ✅ |
| `user.display_name` VARCHAR(64) NULL | ✅ |
| `game_observation` 表存在 | ✅ |
| `game_observation_image` 表存在，`blob_content` 为 LONGBLOB | ✅ |
| `invite_code` 表存在，`code` 有 UNIQUE KEY | ✅ |
| `prompt_template.task_type` 含 `game_observation` | ✅ |

**里程碑 M-DB：✅ 已完成**

### 阶段 C：图片处理与存储抽象（2026-06-09）

| 步骤 | 内容 | 状态 |
|------|------|------|
| C.T | 写测试 `test_image_processing.py`（5）+ `test_image_storage_blob.py`（4）→ 先红 | ✅ |
| C.1 | 新建 `app/integration/image_processing.py`（compress_image + CompressedImage） | ✅ |
| C.2 | 新建 `app/integration/image_storage/base.py`（ImageStorageBackend ABC） | ✅ |
| C.2 | 新建 `app/integration/image_storage/blob_backend.py`（BlobImageStorage） | ✅ |
| C.2 | 新建 `app/integration/image_storage/__init__.py`（get_storage_backend 工厂） | ✅ |
| 测试 | 9/9 passed | ✅ |

### 阶段 D：仓库层（2026-06-09）

| 步骤 | 内容 | 状态 |
|------|------|------|
| D.T | 写 5 个测试文件共 16 用例 → 先红 | ✅ |
| D.1 | 新建 `app/repository/observation_repository.py`（save/get/list/update） | ✅ |
| D.2 | 新建 `app/repository/observation_image_repository.py`（add/list/get/delete） | ✅ |
| D.3 | 扩充 `app/repository/ai_key_repository.py`（key_type 参数，向后兼容默认 'text'） | ✅ |
| D.4 | 新建 `app/repository/invite_code_repository.py`（create/get_active/list/set_active） | ✅ |
| D.5 | 扩充 `app/repository/user_repository.py`（create_pending_user/update_display_name） | ✅ |
| 测试 | 16/16 passed | ✅ |

---

## 阶段 E~I（2026-06-10）

### 阶段 E：AI 视觉客户端 ✅

| 步骤 | 内容 | 状态 |
|------|------|------|
| E.T | `tests/test_vision_base.py`（5）+ `tests/test_observation_client.py`（4）先红 | ✅ |
| E.1 | 新建 `app/integration/ai_client/vision_base.py`（call_ai_vision，60s超时，3次重试） | ✅ |
| E.2 | 新建 `app/integration/ai_client/observation_client.py`（generate_observation，4字段JSON） | ✅ |
| 测试 | 9/9 passed | ✅ |
| 顺带修复 | `app/core/config.py` 补充 IMAGE_STORAGE_BACKEND/IMAGE_MAX_BYTES；安装 Pillow | ✅ |
| 全量回归 | **307 passed, 0 failed** | ✅ |

### 阶段 F：服务层 ✅

| 步骤 | 内容 | 状态 |
|------|------|------|
| F.T | `test_observation_service.py`（4）+ 扩充 `test_auth_service.py`（5）+ `test_invite_service.py`（2）| ✅ |
| F.1+F.2 | 新建 `app/service/observation_service.py`（generate_observation_content + save_observation_with_images） | ✅ |
| F.3 | 扩充 `app/service/auth_service.py`（register_user / approve_user / update_profile_display_name） | ✅ |
| F.4 | 新建 `app/service/invite_service.py`（generate_invite_code / list / toggle） | ✅ |
| 测试 | 28/28 passed | ✅ |
| 全量回归 | **318 passed, 0 failed** | ✅ |

### 阶段 G：Word 导出 ✅

| 步骤 | 内容 | 状态 |
|------|------|------|
| G.T | `test_observation_exporter.py`（8）+ 扩充 `test_export_repository.py`（2）先红 | ✅ |
| G.1 | 新建 `app/integration/word_export/observation_exporter.py`（export_observation，字段映射+图片横排） | ✅ |
| G.2 | Alembic 迁移 `6553de463329`：export_records 新增 observation_id 列 | ✅ |
| G.2 | 扩充 `app/repository/export_repository.py`（observation_id 参数） | ✅ |
| 测试 | 13/13 passed | ✅ |
| 全量回归 | **328 passed, 0 failed** | ✅ |

### 阶段 H：UI 页面 ✅

| 步骤 | 内容 | 状态 |
|------|------|------|
| H.T | `test_observation_ui_helpers.py`（14 用例）先红 | ✅ |
| H.1 | `settings.py` 拆分文本/视觉模型两块（各自独立保存/脱敏/验证） | ✅ |
| H.2+H.3 | 新建 `app/ui/pages/game_observation.py`（表单+上传+生成+保存+导出+历史） | ✅ |
| H.4 | `prompt_mgmt.py` 新增 `game_observation` Tab（含内置提示词） | ✅ |
| H.5 | 新建 `app/ui/pages/register.py`（邀请码注册）+ middleware `/register` 白名单 + login 注册入口 | ✅ |
| H.6 | 新建 `app/ui/pages/profile.py`（显示名 + 修改密码） | ✅ |
| H.7 | `user_admin.py` 新增待审核筛选+审核 + 邀请码管理区块 | ✅ |
| H.8 | `home.py` 新增「个人资料」快捷卡片；`main.py` 注册所有新路由 | ✅ |
| 测试 | 14/14 passed | ✅ |
| 全量回归 | **342 passed, 0 failed** | ✅ |

### 阶段 I：收尾 ✅

| 步骤 | 内容 | 状态 |
|------|------|------|
| I.1 | 审计核查：ai_observation ✅ / export_observation ✅ / register ✅ / approve_user ✅ / invite_code_create ✅ | ✅ |
| I.2 | 更新 progress.md（本文档） | ✅ |
| I.3 | 最终全量回归：342 passed, 0 failed | ✅ |

### 手动验收结果 ✅（2026-06-11）

| 测试项 | 结果 |
|--------|------|
| **M-CORE F-1**：sys_admin 生成邀请码 → `/register` 注册 → 提示等待审核 | ✅ |
| **M-CORE F-2**：sys_admin 审核用户 → 用户登录成功 | ✅ |
| **M-CORE F-3**：停用邀请码 → 注册提示无效 → 启用后恢复 | ✅ |
| **G-1**：上传 1~3 张照片 → 生成观察记录 → 四段内容回填 → 保存 → 导出 docx | ✅ |
| **G-2**：导出后 export_records.observation_id 有值 | ✅ |
| **H-1**：设置页文本/视觉模型分别配置保存 | ✅ |
| **H-2**：游戏观察完整流程（上传→生成→保存→导出→历史列表） | ✅ |
| **H-3**：历史记录重新导出下载 docx 成功 | ✅ |
| **H-4**：邀请码注册 → 审核 → 登录 → 个人资料修改显示名 | ✅ |

**里程碑 M-UI（dev3.0）：✅ 已完成**

**Alembic head：`6553de463329`**

---

## 2026-06-11 — dev3.0 验收 Bug 修复 + 功能补全

### Bug 修复记录

| 编号 | 现象 | 根因 | 修复文件 | 状态 |
|------|------|------|---------|------|
| BL-GO-01 | 上传照片后「已上传：0 张」不更新，控制台 `AttributeError: 'UploadEventArguments' object has no attribute 'content'` | NiceGUI 新版 API 变更：`UploadEventArguments` 已将 `content`（file-like）改为 `file: FileUpload`，且 `FileUpload.read()` 为 async 方法 | `app/ui/pages/game_observation.py` — `handle_upload` 改为 async，`e.content.read()` → `await e.file.read()` | ✅ |
| BL-GO-02 | 历史记录区块加载时 `ValueError: not enough values to unpack (expected 2, got 0)` | `list_observations()` 返回 `list[GameObservation]`，但代码以 `records, _ = await list_observations(...)` 尝试解包为二元组，空列表时崩溃 | `app/ui/pages/game_observation.py` — `refresh_history` 改为 `records = await list_observations(...)` | ✅ |
| BL-GO-03 | 「观察者」字段始终为空，未自动填入登录用户姓名 | `create_access_token()` 生成的 JWT payload 不含 `username`/`display_name`，导致 `get_display_name(user)` 读不到值，始终返回 `""` | `app/auth/jwt.py` — 新增可选参数 `username: str = ""`、`display_name: str \| None = None` 写入 payload；`app/service/auth_service.py` — `login()` 传入 `user.username` / `user.display_name` | ✅ |

### 功能补全

| 项目 | 内容 | 状态 |
|------|------|------|
| 提示词管理新增「游戏观察」Tab | `app/ui/pages/prompt_mgmt.py` — `_TEST_PLACEHOLDER` 增加 `game_observation`；Tabs 增加 `tab_game_observation = ui.tab("游戏观察")`；Tab panels 增加对应面板调用 `_build_task_panel(..., "game_observation")` | ✅ |

### 回归测试

| 覆盖范围 | 结果 |
|---------|------|
| `test_jwt.py`（5）+ `test_auth_service.py`（22）+ `test_observation_repository.py`（4） | **31 passed, 0 failed** |

> **注意**：BL-GO-03 修复后，已登录用户的旧 token 中不含 `username`/`display_name`，需**重新登录**才能使观察者字段自动填入。

---

## 待实现功能（Backlog）

### FEAT-GO-01：生成中状态提示

- **背景**：点击「生成观察记录」后按钮虽有 `loading` 状态（spinner），但首次使用时用户无法感知是否已触发（特别是视觉模型调用时间较长，30~60 秒）。
- **需求**：点击后在页面明显位置显示进度提示（如「⏳ AI 正在分析照片，请稍候……」）；完成/失败时替换为对应的成功/错误提示。
- **影响文件**：`app/ui/pages/game_observation.py` — `do_generate()` 函数，在 `generate_btn.props("loading=true")` 后立即 `show_info("⏳ AI 正在分析照片，请稍候……")` 或类似 toast。
- **优先级**：中（体验问题，不影响功能）。

### FEAT-GO-02：删除已保存观察记录

- **背景**：历史记录列表目前只有「重新导出」按钮，无法删除错误或冗余的观察记录。
- **需求**：每条历史记录右侧增加「删除」按钮，点击后弹出确认对话框，确认后删除 `game_observation` 及关联 `game_observation_image`（CASCADE）。
- **影响文件**：
  - `app/repository/observation_repository.py` — 新增 `delete_observation(session, tenant_id, user_id, observation_id) -> bool`
  - `app/repository/observation_image_repository.py` — 已有 `delete_images_by_observation`，可复用
  - `app/ui/pages/game_observation.py` — `refresh_history()` 中各条记录增加删除按钮 + 确认弹窗 + 刷新历史列表
- **优先级**：高（用户明确需求）。

### FEAT-GO-03：删除每日活动计划记录

- **背景**：`/daily-plan` 页面目前无删除功能，历史计划（草稿、错误记录）无法清除。
- **需求**：在每日活动计划页增加「删除当前草稿」按钮（或在历史列表中每条增加删除按钮），点击确认后删除 `daily_plan` 记录。
- **影响文件**：
  - `app/repository/daily_plan_repository.py` — 新增 `delete_daily_plan(session, tenant_id, user_id, daily_plan_id) -> bool`
  - `app/ui/pages/daily_plan.py` — 增加删除按钮与确认交互
- **优先级**：高（用户明确需求）。

---

## 测试用例统计（截至 2026-06-10）

| 阶段 | 新增文件 | 用例数 | 状态 |
|------|------|--------|------|
| 0 | test_app_shell_menu.py | 10 | ✅ |
| A | test_config_image_settings.py | 3 | ✅ |
| B | test_migrations_smoke.py | 9 | ✅ |
| C | test_image_processing.py + test_image_storage_blob.py | 9 | ✅ |
| D | 5 个仓库层测试文件 | 16 | ✅ |
| E | test_vision_base.py + test_observation_client.py | 9 | ✅ |
| F | test_observation_service.py + 扩充 test_auth_service + test_invite_service | 28 | ✅ |
| G | test_observation_exporter.py + 扩充 test_export_repository | 13 | ✅ |
| H | test_observation_ui_helpers.py | 14 | ✅ |
| **合计（游戏观察子系统新增）** | | **111** | ✅ |
| **总计** | | **342 passed** | ✅ |
| D.5 | 扩充 `app/repository/user_repository.py`（create_pending_user/update_display_name） | ✅ |
| 测试 | 16/16 passed（新增）| ✅ |

**全量回归（pytest tests/ -q）**

| 指标 | 值 |
|------|----|
| 总用例数 | **298 passed** |
| 失败 | 0 |
| 耗时 | 20.43s |

---

### 阶段 E：AI 视觉客户端（待开发）
- [ ] 写测试 `tests/test_vision_base.py`（5 用例）+ `tests/test_observation_client.py`（4 用例）
- [ ] `app/integration/ai_client/vision_base.py`
- [ ] `app/integration/ai_client/observation_client.py`

### 阶段 F：服务层（待开发，里程碑 M-CORE）
- [ ] 写测试（`test_observation_service.py` 4 用例 / 扩充 `test_auth_service.py` 5 用例 / `test_invite_service.py` 2 用例）
- [ ] `app/service/observation_service.py`
- [ ] 扩充 `app/service/auth_service.py`（register_user / approve_user / update_profile_display_name）
- [ ] `app/service/invite_service.py`

### 阶段 G：Word 导出（待开发）
- [ ] 写测试 `test_observation_exporter.py`（8 用例）+ 扩充 `test_export_repository.py`（2 用例）
- [ ] `app/integration/word_export/observation_exporter.py`
- [ ] `export_record` 表新增 `observation_id` 列（迁移）

### 阶段 H：UI 页面（待开发，里程碑 M-UI）
- [ ] 写测试 `test_observation_ui_helpers.py`（3 用例，纯函数）
- [ ] H1: `settings.py` 拆分文本/视觉模型配置
- [ ] H2: 新建 `app/ui/pages/game_observation.py`（观察主页面）
- [ ] H3: 观察历史（同页或子区块）
- [ ] H4: `prompt_mgmt.py` 新增 `game_observation` Tab
- [ ] H5: 新建 `app/ui/pages/register.py` + 中间件白名单
- [ ] H6: 新建 `app/ui/pages/profile.py`
- [ ] H7: `user_admin.py` 扩展（邀请码 + 待审核）
- [ ] H8: `home.py` 新增导航按钮

### 阶段 I：全量回归（待开发）
- [ ] 全量 `pytest tests/ -v` 全绿（目标 ~330+ passed）
- [ ] 更新 `architecture.md`

---

## 测试用例统计（截至 2026-06-09）

| 阶段 | 文件 | 用例数 | 状态 |
|------|------|--------|------|
| 0 | test_app_shell_menu.py | 10 | ✅ |
| A | test_config_image_settings.py | 3 | ✅ |
| B | test_migrations_smoke.py | 9 | ✅ |
| C | test_image_processing.py + test_image_storage_blob.py | 9 | ✅ |
| D | test_observation_repository.py | 4 | ✅ |
| D | test_observation_image_repository.py | 3 | ✅ |
| D | test_invite_code_repository.py | 3 | ✅ |
| D | test_ai_key_repository_keytype.py | 3 | ✅ |
| D | test_user_repository_displayname.py | 3 | ✅ |
| **已完成小计** | | **47** | ✅ |
| E | test_vision_base.py + test_observation_client.py | 9 | ⏳ |
| F | test_observation_service.py + 扩充 test_auth_service.py + test_invite_service.py | 11 | ⏳ |
| G | test_observation_exporter.py + 扩充 test_export_repository.py | 10 | ⏳ |
| H | test_observation_ui_helpers.py | 3 | ⏳ |
| **全量（含已有 251 基础用例）** | | **298 passed** | ✅ |
