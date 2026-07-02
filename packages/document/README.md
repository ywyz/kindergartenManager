# @kindergarten/document

文档导出边界包。

## 当前职责

- Word 模板样式配置。
- 可调整表头、标题、正文文字字体、大小、段落和行间距。
- 生成包含中文、表格和图片的 `.docx` Buffer。
- 后续扩展 Excel 导入导出。

## 验证

```bash
pnpm --filter @kindergarten/document typecheck
pnpm test:gate
```

## P0 文档

见 `memory-bank/dev4.0/p0-word-spike.md`。
