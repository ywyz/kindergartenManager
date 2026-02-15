"""诊断模板结构"""
from docx import Document

doc = Document('examples/teacherplan.docx')
print("模板行标签：")
for i, row in enumerate(doc.tables[0].rows):
    if len(row.cells) > 0:
        label = row.cells[0].text.strip()
        print(f"{i}: {label}")
