# dev4.0 P0 — AI Key Crypto Spike

## 结果指标

证明 dev4.0 可以安全保存用户各自 AI Key：密文入库、AAD 绑定租户/用户/key 类型、明文脱敏展示、日志文本可脱敏。

## 范围

- 在 `packages/auth` 建立 AI Key 加密合同。
- 使用 Node `crypto` 的 AES-256-GCM。
- 每条记录包含 algorithm、keyVersion、iv、ciphertext、authTag。
- AAD 绑定 `tenantId`、`userId`、`keyKind`，防止密文跨用户或跨类型误用。
- 提供 `maskSecret` 和 `redactSecretsFromText`。

## 不做

- P0 不实现 AI Key 数据库表。
- P0 不实现密钥轮换任务。
- P0 不实现设置页面。
- P0 不接真实 AI。

## 加密合同

- 加密：`encryptSecret({ plaintext, masterKey, keyVersion, aad })`。
- 解密：`decryptSecret({ record, masterKey, aad })`。
- AAD：`tenantId:userId:keyKind`。
- keyKind：`text` 或 `vision`。
- masterKey 不写入返回值。

## Gate Tests

```bash
pnpm --filter @kindergarten/auth typecheck
pnpm test:gate
```

测试覆盖：

- 密文不包含明文。
- 同一明文两次加密结果不同。
- 正确 AAD 可解密。
- 错误 tenant/user/keyKind 无法解密。
- 错误 masterKey 无法解密。
- 脱敏显示只保留末尾少量字符。
- 日志文本中的明文 Key 被替换。

## 失败边界

- 如果密文记录泄露明文，测试失败。
- 如果 AAD 不匹配仍能解密，测试失败。
- 如果错误主密钥仍能解密，测试失败。
