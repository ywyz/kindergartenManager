# @kindergarten/web

dev4.0 React/Vite 前端入口。

## 当前职责

- 验证前端可以消费共享角色合同。
- 验证前端可以从共享合同生成角色和高权限 action view model。
- 后续承载线上唯一系统的教师、年级组长、业务园长、园长、系统管理员界面。

## 验证

```bash
pnpm --filter @kindergarten/web typecheck
pnpm --filter @kindergarten/web build
```

## P0 文档

见 `memory-bank/dev4.0/p0-web-contract-smoke.md`。
