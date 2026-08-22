# `services/` 状态说明

当前 `main` 没有独立微服务实现。本目录仅保留未来拆分的占位说明；当前 AI、Word 和节假日能力都在主应用 `app/integration/` 中运行，`docker-compose.yml` 也没有对应服务。

如果未来需要拆分，必须先完成独立 ADR 和可运行契约，至少回答：

- 拆分解决的容量、故障隔离、部署或所有权问题。
- 数据所有权与事务边界。
- 服务鉴权、密钥、超时、重试和幂等。
- OpenAPI/消息契约与版本兼容。
- 本地开发、Compose、监控和回滚。
- 主应用从 in-process adapter 迁移的双轨验证。

建议顺序：

1. 先保持 `app/integration/` 的深接口稳定。
2. 为候选边界写 contract test。
3. 创建最小服务骨架和 `/health`。
4. 在不改变 service 调用方的前提下增加远程 adapter。
5. 完成故障/安全/部署验收后再加入 Compose。

在上述门禁前，不创建空目录来暗示服务已经交付。
