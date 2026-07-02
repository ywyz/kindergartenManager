# @kindergarten/storage

对象存储基础包。

## 当前职责

- 生成稳定对象 key。
- 禁止用户输入作为路径片段直接拼接。
- 限制文件扩展名只保留安全字符。
- 校验图片、Word 模板、Excel 上传的大小、MIME、扩展名和文件头。
- 生成包含 key、bytes、sha256、mimeType、extension 的文件元数据。

## 验证

```bash
pnpm --filter @kindergarten/storage typecheck
pnpm test:gate
```

## P0 文档

见 `memory-bank/dev4.0/p0-storage-upload-spike.md`。
