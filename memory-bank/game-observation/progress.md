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

### 阶段 A：基础设施
- [ ] 写测试 `tests/test_config_image_settings.py`（3 用例）
- [ ] `requirements.txt` 新增 `Pillow>=10.0.0`
- [ ] `app/core/config.py` 新增 IMAGE_STORAGE_BACKEND / IMAGE_MAX_BYTES

### 阶段 B：数据模型与迁移
- [ ] 写测试（扩充 `test_migrations_smoke.py`，5 用例）
- [ ] B1: ai_api_key.key_type 列（ENUM text/vision）
- [ ] B2: user.display_name 列（VARCHAR 64 NULL）
- [ ] B3: game_observation 表
- [ ] B4: game_observation_image 表（LargeBinary/LONGBLOB）
- [ ] B5: invite_code 表
- [ ] B6: prompt_template.task_type 扩展 game_observation

### 阶段 C：图片处理与存储
- [ ] 写测试 test_image_processing.py（5）+ test_image_storage_blob.py（3）
- [ ] app/integration/image_processing.py（compress_image）
- [ ] app/integration/image_storage/（base + blob_backend + factory）

### 阶段 D：仓库层
- [ ] 写测试（5 个文件，共 18 用例）
- [ ] observation_repository.py / observation_image_repository.py / invite_code_repository.py
- [ ] 扩充 ai_key_repository.py（key_type 参数）
- [ ] 扩充 user_repository.py（create_pending_user / update_display_name）

### 阶段 E：AI 视觉客户端
- [ ] 写测试 test_vision_base.py（5）+ test_observation_client.py（4）
- [ ] vision_base.py / observation_client.py

### 阶段 F：服务层（里程碑 M-CORE）
- [ ] 写测试（3 个文件，共 11 用例）
- [ ] observation_service.py / 扩充 auth_service.py / invite_service.py

### 阶段 G：Word 导出
- [ ] 写测试 test_observation_exporter.py（8）+ 扩充 test_export_repository.py（2）
- [ ] observation_exporter.py / export_record 新增 observation_id 列

### 阶段 H：UI 页面（里程碑 M-UI）
- [ ] 写测试 test_observation_ui_helpers.py（3 用例）
- [ ] H1~H8：8 个页面改动（game_observation/register/profile/settings 扩展等）

### 阶段 I：全量回归
- [ ] 目标 ~298 passed（原 261 + 新增 ~37）
- [ ] 更新 architecture.md

---

## 测试用例统计

| 阶段 | 文件 | 用例数 | 状态 |
|------|------|--------|------|
| 0 | test_app_shell_menu.py | 10 | ✅ 已通过 |
| A | test_config_image_settings.py | 3 | ⏳ |
| B | test_migrations_smoke.py（扩充）| 5 | ⏳ |
| C | test_image_processing + test_image_storage_blob | 8 | ⏳ |
| D | 5 个仓库测试文件 | 18 | ⏳ |
| E | test_vision_base + test_observation_client | 9 | ⏳ |
| F | 3 个服务测试文件 | 11 | ⏳ |
| G | test_observation_exporter + 扩充 | 10 | ⏳ |
| H | test_observation_ui_helpers | 3 | ⏳ |
| **合计** | | **~77** | |
