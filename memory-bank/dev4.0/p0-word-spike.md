# dev4.0 P0 — Word Export Spike

## 结果指标

证明 dev4.0 可以从结构化输入生成合法 `.docx`，并能在导出时调整表头、标题、正文的字体、字号、段前段后和行距。

## 范围

- 在 `packages/document` 建立 Word 导出基础合同。
- 使用 `docx` 生成 `.docx`。
- 使用 `jszip` 在测试中读取 OpenXML，验证输出内容和样式。
- 覆盖中文标题、正文、多列表格、图片、表头样式、标题样式、正文段落样式。

## 不做

- 不迁移旧 Python Word exporter。
- 不读取旧 `.docx` 模板。
- 不实现完整业务子系统导出。
- 不写文件到磁盘，P0 只返回 `Buffer` 供后续 API 或 worker 保存。

## 输入合同

`generateStyledWordDocument` 接收：

- `title`：文档标题。
- `paragraphs`：正文段落列表。
- `table`：表头和数据行。
- `style`：可覆盖默认 Word 样式。
- `image`：可选 PNG/JPG/GIF/BMP 图片数据和尺寸。

## Gate Tests

```bash
pnpm test:gate
pnpm --filter @kindergarten/document typecheck
```

测试必须解包 `.docx`，直接断言：

- `word/document.xml` 包含中文标题、正文和表格内容。
- `word/document.xml` 包含 `w:tbl`。
- `word/document.xml` 包含 `w:drawing`。
- `word/media/*` 存在图片文件。
- 字体、字号、段前段后和行距写入 OpenXML。

## 失败边界

- 如果只生成纯文本而没有表格，测试失败。
- 如果图片没有写入 `word/media`，测试失败。
- 如果中文字体没有写入 `w:eastAsia`，测试失败。
- 如果行距和段落间距未进入 XML，测试失败。
