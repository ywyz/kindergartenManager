# 游戏观察子系统 — 分步测试计划

> 配套：[design.md](design.md)、[dev-plan.md](dev-plan.md)。
> 框架：`pytest` + `pytest-asyncio` + `aiosqlite`（沿用 `tests/conftest.py` 既有 fixture）。
> 原则：AI 调用、视觉调用、Word、存储均用 mock / fixture 隔离；每个 service 函数必须有单测；
> 查询测试需覆盖 tenant 隔离。运行：`pytest tests/ -v`；单文件 `pytest tests/test_xxx.py -v`。
>
> 每个开发步骤完成后运行其对应测试，全绿再继续；阶段里程碑做一次全量回归。

---

## 阶段 0：界面重构

> NiceGUI 布局以手动联调为主；可单测的纯逻辑（菜单项按角色过滤、active 高亮判定）抽出单测。

### T0-1（0.1）`test_app_shell_menu.py`
- 菜单项按角色过滤：`teacher` 看不到「账号管理/邀请码」；`sys_admin` 可见。
- `active` 高亮：传入某 key 时对应菜单标记选中。
- 显示名回退：display_name 为空时顶栏展示 username。

### T0-2（0.2 / 0.3 / 0.4）手动联调清单（人工）
- 登录后进入仪表盘：欢迎信息、快捷卡片可跳转、班级信息正确。
- settings / daily-plan / prompts / user-admin 在新布局下功能与原先一致（拆分/生成/导出/保存/账号操作）。
- 左侧菜单分组正确、当前页高亮、退出可用。
- 访问 `/date-test` 返回 404 或被路由守卫处理（页面已删除）。

### T0-3（0.5）回归
- `pytest tests/ -v` 全绿；若存在引用 `date_test` 的测试需同步删除/调整。

---

## 阶段 A：基础设施

### TA1（对应 A1/A2）依赖与配置
- `test_config_image_settings.py`
  - `IMAGE_STORAGE_BACKEND` 默认 `mysql_blob`。
  - `IMAGE_MAX_BYTES` 默认 1048576。
  - `import PIL` 成功。

---

## 阶段 B：模型与迁移

### TB1（B1）ai_api_key.key_type
- `test_migrations_smoke.py::test_ai_key_has_key_type`
  - 全量迁移后 `key_type` 列存在；新建记录默认 `text`；可写 `vision`。

### TB2（B2）user.display_name
- `display_name` 可空；默认 None；可更新。

### TB3（B3/B4）观察相关表
- 建表后可插入/查询 `game_observation`；隔离字段非空约束生效。
- `game_observation_image.blob_content` 可存取二进制（SQLite LargeBinary）。

### TB4（B5）invite_code
- `code` 唯一约束：插入重复 code 抛 IntegrityError。

### TB5（B6）prompt 枚举扩展
- 可保存 `task_type='game_observation'` 的 PromptTemplate。

> 迁移测试用临时 sqlite/内存库执行 upgrade head + 简单 downgrade 冒烟。

---

## 阶段 C：图片处理与存储

### TC1（C1）`test_image_processing.py`
- 小图（<1MB）：原样或轻处理，返回 ≤1MB，mime/尺寸正确。
- 大图（构造 >1MB）：压缩后 `file_size <= IMAGE_MAX_BYTES`。
- 非图片字节：抛业务异常。
- 透明 PNG → 处理后仍可解码（无异常）。
- 极小尺寸图：不崩溃。

### TC2（C2）`test_image_storage_blob.py`
- `BlobImageStorage.put` 后 `get` 得到**完全相同**字节。
- 工厂 `get_storage_backend` 默认返回 blob 后端。
- 未知后端名 → 明确异常。

---

## 阶段 D：仓库层

### TD1（D1）`test_observation_repository.py`
- `save_observation` 返回带 id；字段持久化正确。
- `get_observation_by_id` 携带 tenant 过滤：跨 tenant 取不到（返回 None）。
- `list_observations` 分页 + 日期范围 + 班级过滤；按日期降序稳定排序。
- `update_observation` 仅改目标字段，updated_at 变化。

### TD2（D2）`test_observation_image_repository.py`
- `add_image` 多张后 `list_images_by_observation` 按 `image_index` 升序返回。
- `get_image` 跨 tenant 取不到。
- `delete_images_by_observation` 清空对应记录。

### TD3（D3）`test_ai_key_repository.py`（扩充）
- 保存 `key_type='text'` 与 `key_type='vision'` 各一条，二者均 active 且互不 deactivate。
- `get_active_ai_key(key_type='vision')` 只返回 vision；text 同理。
- 再次保存同类型使旧记录 inactive，另一类型不受影响。

### TD4（D4）`test_invite_code_repository.py`
- `create_code` 生成可查询；`get_active_by_code` 命中。
- `set_code_active(False)` 后 `get_active_by_code` 返回 None。

### TD5（D5）`test_user_repository.py`（扩充）
- `create_pending_user` → `is_active=False`、`role=teacher`。
- 同 tenant 同 username 重复 → 唯一性报错。
- `update_display_name` 生效。

---

## 阶段 E：AI 视觉客户端

### TE1（E1）`test_vision_base.py`
- mock httpx：返回合法 JSON content → 解析为 dict。
- HTTP 400/500 → `AiCallError`，message 含响应体摘要。
- 超时 → `AiCallError`。
- content 非 JSON → `AiParseError`。
- 校验请求体含多模态 `image_url`（data url）结构。

### TE2（E2）`test_observation_client.py`
- mock 返回 4 字段 JSON → 正确映射 observation_goal/record/evaluation/strategy。
- 缺字段 → `AiParseError`（或既有降级策略）。
- 空 images 列表 → 抛异常（至少 1 张）。
- 自定义 system_prompt 覆盖默认；图片正确转 base64 data-url（mock 校验 payload）。

---

## 阶段 F：服务层

### TF1（F1）`test_observation_service.py`
- 未配置视觉 Key → `ConfigError`。
- 正常：mock vision client + mock 压缩 → 返回 4 字段 + 压缩图片；触发 `log_audit("ai_observation")`（可用 caplog 或 mock 校验）。
- DB 提示词激活版本存在时覆盖默认 prompt（mock get_active_prompt）。

### TF2（F2）保存编排
- `save_observation_with_images`：写记录 + N 张图片，取回一致；图片走存储后端（mock/blob）。
- 中途失败回滚（构造图片写入异常 → 观察记录不残留，或按事务策略校验）。

### TF3（F3）`test_auth_service.py`（扩充）
- `register_user` 无效/停用邀请码 → 业务异常。
- 有效邀请码 → 创建 `is_active=False, role=teacher`，tenant 来自邀请码。
- 同 tenant 重复用户名 → 异常。
- `approve_user` 后用户可被 `authenticate`（启用后登录成功）。
- `update_profile_display_name` 生效。

### TF4（F4）`test_invite_service.py`
- `generate_invite_code` 生成随机唯一 code；toggle 启停可用。

---

## 阶段 G：Word 导出

### TG1（G1）`test_observation_exporter.py`
- 导出返回非空 bytes，可被 `python-docx` 重新打开。
- 标题段落 `xx` 被替换为大环境（户外/室内/公共）。
- 各单元格内容正确：班级/日期/起止时间/成人/儿童/观察者/姓名/年龄/观察环境/观察目标/记录/评价/策略。
- 模板示例文本被清空（不残留「王鹤宁、侯舒妍」）。
- 图片：传入 1 / 2 / 3 张时，R5 观察记录单元格内图片数量正确，且位于文字之后。
- 中文 run 字体为宋体且设置了 `w:eastAsia`。
- 模板缺失（指向不存在路径）→ 降级从零构表不报错。

### TG2（G2）导出记录
- `test_export_repository.py`（扩充）：观察导出写入 export_records，可按 tenant 查询；`observation_id` 关联正确（若采用新列）。

---

## 阶段 H：UI（以可单测逻辑为主）

> NiceGUI 页面交互以手动联调为主；可单测的纯函数（字段组装、校验、文件名生成）抽出单测。

### TH1 字段/文件名
- 导出文件名规则单测：`{tenant}_{user}_{grade}_{class}_{日期}_游戏观察.docx`。
- 大环境取值校验：非 户外/室内/公共 → 校验失败。
- 图片数量校验：0 张禁用生成；>3 张被拒。

### TH2 手动联调清单（人工）
- 设置页分别保存文本/视觉模型并回显脱敏。
- 观察页：上传 1~3 图 → 生成 → 回填可编辑 → 保存 → 导出下载 → 历史可见并重新导出。
- 提示词页 game_observation Tab：保存新版本 → 回滚 → 生效。
- 注册：无效邀请码报错；有效注册后提示待审核；管理员审核后可登录。
- 个人资料：改显示名 → 观察页观察者默认值更新。
- 账号管理：生成邀请码、启停、待审核筛选与启用。
- 权限：teacher 访问 /user-admin 被拦截；未登录访问 /game-observation 跳登录；/register 免登录可达。

---

## 阶段 I：回归与基准
- 全量 `pytest tests/ -v` 全绿（既有用例 251 passed 不回归 + 新增用例）。
- 记录新增用例数与最终通过数，更新 `progress.md`。

---

## 测试用例数量预估（指导值）
| 模块 | 文件 | 用例数 |
|------|------|--------|
| 布局菜单 | test_app_shell_menu | 3 |
| 配置 | test_config_image_settings | 3 |
| 迁移 | test_migrations_smoke（扩充） | 5 |
| 图片处理 | test_image_processing | 5 |
| 存储 | test_image_storage_blob | 3 |
| 观察仓库 | test_observation_repository | 5 |
| 图片仓库 | test_observation_image_repository | 4 |
| AI Key 仓库 | test_ai_key_repository（扩充） | 3 |
| 邀请码仓库 | test_invite_code_repository | 3 |
| 用户仓库 | test_user_repository（扩充） | 3 |
| 视觉基座 | test_vision_base | 5 |
| 观察客户端 | test_observation_client | 4 |
| 观察服务 | test_observation_service | 4 |
| 注册/资料 | test_auth_service（扩充） | 5 |
| 邀请码服务 | test_invite_service | 2 |
| Word 导出 | test_observation_exporter | 8 |
| 导出记录 | test_export_repository（扩充） | 2 |
| UI 纯函数 | test_observation_ui_helpers | 3 |
| **合计** | | **约 70** |
