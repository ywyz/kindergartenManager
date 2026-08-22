# ADR-0004：AI 适配器、教师采用与固定 Word 模板边界

- 状态：接受
- 日期：2026-08-22

## 背景

多个教学模块复用文本/视觉 AI 和固定 Word 模板。若页面直接调用 HTTP、AI 输出直接覆盖输入或 exporter 自行发明布局，将导致安全、可测性和模板保真失控。

## 决策

- 外部 AI 调用只存在于 `app/integration/ai_client/`，service 负责用例编排。
- AI Key 加密存储、短暂解密，不进入日志。
- AI 结果必须结构校验，并由教师编辑/采用；原始教师内容按模块需要保留。
- Word exporter 复制并填充仓库中的固定模板，中文字体、图片、差异和指标位置属于契约。
- 自动结构测试与真实 Word/Office 人工验收是独立门禁。

## 后果

- 新 AI 任务需定义输入最小化、输出 schema、失败降级和审计。
- 模板变更需同步映射测试、用户文档和人工验收。
- 模板缺失时的降级输出不能作为正式模板验收通过证据。

## 与受控 Agent 的关系

本 ADR 描述的是已有单次 AI 生成流：应用组织一次输入并接收结构化结果。
[ADR-0005](ADR-0005-controlled-ai-agent-runtime.md) 另行约束未来的 Tool-calling Agent 循环。引入 Agent
不改变本 ADR 的密钥、Provider 和教师最终采用边界，也不能将已有 AI 生成函数直接暴露成任意 Agent Tool。
