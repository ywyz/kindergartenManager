# 幼儿园每日活动计划系统 - 待办事件清单

> 最后更新:2026-04-18  
> 分支:`feature/daily-plan`  
> 当前进度:Phase 1-2 已实现并验证;Phase 3-5 代码已存在,待端到端测试

---

## 🔥 优先级 1:端到端验证(代码已就绪)

### Phase 3 — 一日活动计划 AI 生成
- [ ] 在 `/settings` 填写「区域游戏内容」「户外游戏内容」并保存
- [ ] 进入 `/daily-plan` 选日期,确认周次/星期/工作日提示正确
- [ ] 点击「AI 生成活动内容」,验证 4 块内容(晨间活动/晨间谈话/室内区域/户外游戏)正确填充
- [ ] 验证临近节假日时晨间谈话提示词带有节日上下文

### Phase 4 — Word 导出
- [ ] 完成一份完整计划后点击「导出 Word」
- [ ] 检查表头(第几周/月日/星期)填充位置正确
- [ ] 检查 8 大项 24+ 子字段对应到模板单元格无错位
- [ ] 检查 AI 修改过的「活动过程」段落显示**红色字体**
- [ ] 验证 `/history` 历史记录页面可重新导出旧计划

### Phase 5 — 提示词管理
- [ ] 在 `/prompts` 验证 6 个分类的增/删/改/激活
- [ ] 验证「测试」按钮可发送测试内容并返回 AI 响应
- [ ] 修改某个提示词并激活后,确认 `ai_service` 真的使用了新提示词(不是默认值)

---

## ⚠️ 优先级 2:已识别的代码缺口与风险点

| # | 位置 | 问题描述 | 状态 |
|---|---|---|---|
| 1 | `app/pages/daily_plan.py` | 集体活动栏不会自动从当天「教案拆分」结果继承数据,需用户重复输入 | TODO |
| 2 | `app/services/date_utils.py` | 节假日列表硬编码,不含调休,需接入外部 API 或维护年度数据 | TODO |
| 3 | DB schema `daily_plans` | 缺 `(plan_date, grade, class_name)` 唯一索引,可能产生重复记录 | TODO |
| 4 | `app/services/ai_service.py` | JSON 解析失败仅抛异常,未做 1-2 次让模型修正的重试 | ✅ 已完成 |
| 5 | `app/pages/settings.py` | `area_content`/`outdoor_content` 只有单一文本框,Plan 2.1 要求"可保存多条候选" | TODO |
| 6 | 学期设置 | 仅最近一条生效,无法切换/查看历史学期 | TODO |
| 7 | `.env` `APP_SECRET_KEY` | 仍是占位符,加密强度=0,**必须立刻替换为强随机值** | **紧急** |
| 8 | `app/pages/lesson_split.py` | 拆分页有独立日期,应与一日计划日期共用 | 处理中 |
| 9 | `app/pages/lesson_split.py` → `daily_plan.py` | 教案拆分模块应内嵌到一日计划页面,统一保存与导出 Word | 处理中 |
| 10 | `_DEFAULT_PROMPTS["process_modify"]` | 模型偶尔返回完整 JSON 而非纯文本,导致"AI 修改版"显示 JSON;需在提示词层显式禁止 JSON,并在调用层兜底剥离 | 处理中 |
| 11 | `_DEFAULT_PROMPTS["lesson_split"]` + `_KEY_ALIASES` | 模型把目标键写成"活动目标"被错误归一化为 `activity_goal`,导致 `result.get("goal")` 为空、目标不显示 | 处理中 |
| 12 | `app/services/word_export.py` Row 11 | 导出后「活动过程」整段文字全部变红,实际仅【AI修改】标记的环节(段落)需变红,其余保持黑色;需按段落级判定 | **TODO** |

---

## 🆕 新增功能需求

- [ ] **多 AI 并发批量生成**:晨间活动/晨间谈话/室内区域/户外游戏目前是串行 4 次 AI 请求,改为 `asyncio.gather` 或线程池并发,显著降低等待时间
- [ ] **多 AI 负载均衡**:`ai_config` 表支持配置多条激活的 AI(不同 url/key/model),`get_ai_service` 按轮询/随机/权重策略分发请求,避免单 Key 限速;失败自动切换下一个

> ⚠️ 修改 `APP_SECRET_KEY` 后,旧的 Fernet 加密 API Key 无法解密,需要在设置页**重新保存一次 AI Key**

---

## 📋 优先级 3:加分项(计划文件外建议)

- [ ] `templates/MAPPING.md`:记录 docx 单元格行/列 ↔ Python 数据字段对应关系,模板调整时有据可查
- [ ] 导出文件命名规范:`{年级}{班级}_{YYYY-MM-DD}_{第N周周X}.docx`
- [ ] 启动自检页:展示数据库连通性、AI 配置存在性、Word 模板存在性三项检查
- [ ] AI 调用日志:记录每次请求的 prompt/响应,便于调试与提示词优化
- [ ] 导出按钮文案区分:「保存并导出」vs 单独「导出」,避免用户漏点保存

---

## 📌 已完成

- [x] **Phase 1**:项目骨架、5 张表自动建库、NiceGUI 路由与导航、日期工具、Fernet 加密
- [x] **Phase 2**:教案 AI 拆分页面、AI 服务封装、活动过程 diff 高亮、保存与导出按钮
- [x] **Bug 修复**:`get_ai_service` 未解密 Key、JSON 提取容错、日期事件绑定
- [x] **性能修复**:所有阻塞 IO(AI/DB/Word)放入 `nicegui.run.io_bound` 线程池,解决"JavaScript did not respond within 1.0 s"

---

## 🚀 推荐推进顺序

1. **立刻**:替换 `APP_SECRET_KEY` 为强随机值,重新保存 AI Key
2. **本轮**:跑通 Phase 3 → Phase 4 端到端,把出现的问题反馈
3. **下轮**:修复 #1(集体活动继承)、#3(唯一索引)、#4(AI 重试)三项加固
4. **后续迭代**:节假日 API 接入、多条游戏内容、学期切换、自检页等加分项
