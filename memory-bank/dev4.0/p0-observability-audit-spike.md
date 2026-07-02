# dev4.0 P0 — Observability/Audit Spike

## 结果指标

证明 dev4.0 的高风险操作可以生成结构化审计事件，并且审计 metadata 不会泄露 API Key、密码、Token、Authorization header 等敏感内容。

## 范围

- 在 `packages/observability` 建立审计事件合同。
- 审计事件包含 eventId、tenantId、actorUserId、action、target、outcome、riskLevel、reason、metadata、occurredAt。
- 对 metadata 做递归脱敏。
- 失败和拒绝事件必须包含 reason。

## 不做

- P0 不接日志后端。
- P0 不接 OpenTelemetry。
- P0 不写数据库审计表。
- P0 不实现 API middleware。

## Gate Tests

```bash
pnpm --filter @kindergarten/observability typecheck
pnpm test:gate
```

测试覆盖：

- 审计事件结构稳定。
- `denied` 和 `failed` 必须填写 reason。
- metadata 中的 apiKey、password、token、authorization、cookie 被递归脱敏。
- metadata 字符串里的 `sk-*` 明文 Key 被替换。
- 生成后的 JSON 不包含原始秘密。

## 失败边界

- 如果审计事件 JSON 含有明文 AI Key，测试失败。
- 如果权限拒绝事件没有 reason，测试失败。
- 如果 action 格式不可审计，测试失败。
