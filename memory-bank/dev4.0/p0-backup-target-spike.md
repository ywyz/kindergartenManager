# dev4.0 P0 — Backup Target Spike

## 结果指标

证明 dev4.0 备份层可以把备份文件写入远端目标、读回并做 SHA-256 校验，同时能把认证失败和完整性失败明确分类。

## 范围

- 在 `packages/backup` 建立备份目标合同。
- 建立 WebDAV 目标实现，使用 Node 24 内置 `fetch`，不额外引入 WebDAV 依赖。
- 建立 verified transfer 包装层：上传后读回校验，下载时按 manifest 校验。
- 保留 `BackupTargetKind = "s3" | "webdav"`，业务层只依赖统一合同。
- Gate tests 使用内存目标和 fake fetch，不访问真实外网。

## 不做

- 不接入真实 S3 账号。
- 不接入真实 WebDAV 服务。
- 不执行数据库备份命令。
- 不实现恢复 UI。

## 输入合同

- `BackupObjectTarget`：远端目标必须实现 `putObject` 和 `getObject`。
- `writeVerifiedBackupObject`：写入后读回，返回含 `path`、`bytes`、`sha256` 的 manifest。
- `readVerifiedBackupObject`：按 manifest 读回并校验。
- `createWebDavBackupTarget`：把 WebDAV URL、鉴权配置和 `fetch` 封装成目标。

## Gate Tests

```bash
pnpm --filter @kindergarten/backup typecheck
pnpm test:gate
```

测试必须覆盖：

- WebDAV PUT/GET 请求路径和 Authorization header。
- 上传后读回 SHA-256 校验成功。
- 读回内容被篡改时抛出完整性错误。
- WebDAV 401/403 映射为认证错误。

## 失败边界

- 如果下载内容和 manifest hash 不一致，必须失败。
- 如果 WebDAV 认证失败，必须失败且错误类型可识别。
- 如果路径为空或包含非法字符，必须失败。
