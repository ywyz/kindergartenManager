# @kindergarten/auth

认证与授权边界包。

## 当前职责

- RBAC 合同。
- workflow action 授权判断。
- `self`、`grade`、`tenant`、`system` scope 判断。
- 高风险动作返回 `auditAction`。
- AI Key AES-256-GCM 加密、AAD 绑定、脱敏展示和日志脱敏。

## 后续职责

- 登录、会话、密码策略。
- Session Cookie、CSRF、密码哈希。
- API middleware。

## 验证

```bash
pnpm --filter @kindergarten/auth typecheck
pnpm test:gate
```

## P0 文档

见 `memory-bank/dev4.0/p0-auth-rbac-spike.md`。
