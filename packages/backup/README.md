# @kindergarten/backup

备份与恢复基础包。

## 当前职责

- 定义 S3/WebDAV 备份 manifest。
- 校验文件大小和 SHA-256。
- 保证 manifest 文件顺序稳定，便于审计和 diff。
- 提供 WebDAV 备份目标和上传后读回校验。

## 验证

```bash
pnpm --filter @kindergarten/backup typecheck
pnpm test:gate
```

## P0 文档

见 `memory-bank/dev4.0/p0-backup-target-spike.md`。
