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
