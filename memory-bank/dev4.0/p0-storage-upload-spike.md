# dev4.0 P0 — Storage Upload Safety Spike

## 结果指标

证明 dev4.0 文件上传不会使用用户文件名拼接路径，并且可以在入库前生成可审计的文件元数据：对象 key、大小、SHA-256、MIME、扩展名和资产类型。

## 范围

- 在 `packages/storage` 建立上传校验合同。
- 校验图片、Word 模板、Excel 文件的扩展名、MIME、大小和文件头。
- 生成 tenant-scoped 对象 key，不使用用户上传文件名。
- 计算 SHA-256，返回可入库的 `StoredObjectMetadata`。

## 不做

- P0 不接真实 S3/WebDAV。
- P0 不实现浏览器上传 UI。
- P0 不压缩图片。
- P0 不解析 Excel 内容。

## 支持类型

- 图片：PNG、JPEG，最大 10MB。
- Word 模板：DOCX，最大 20MB。
- Excel：XLSX，最大 20MB。

## Gate Tests

```bash
pnpm --filter @kindergarten/storage typecheck
pnpm test:gate
```

测试覆盖：

- 上传文件名包含路径时，生成的 key 不包含用户文件名。
- PNG/JPEG/DOCX/XLSX 文件头校验。
- 扩展名、MIME 和文件头不一致时拒绝。
- 超过大小限制时拒绝。
- object id 不允许包含路径分隔符。

## 失败边界

- 如果 key 中出现用户文件名，测试失败。
- 如果 path-like object id 被接受，测试失败。
- 如果 MIME/扩展名和文件头不一致仍通过，测试失败。
