"""读取导出的Word文档"""
from docx import Document

# 读取其中一个文档
doc = Document('output/教案_20251112.docx')

print("=== Word文档内容（表格0）===")
for i, row in enumerate(doc.tables[0].rows):
    if len(row.cells) >= 2:
        label = row.cells[0].text.strip()[:30]
        content = row.cells[1].text.strip()[:100]
        print(f"{i}: [{label}] => {content}")
