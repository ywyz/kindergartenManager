"""
Word文档操作模块
"""

from pathlib import Path
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from .models import WORD_FONT_NAME, WORD_FONT_SIZE, WORD_INDENT_FIRST_LINE


def apply_run_style(run):
    """设置运行样式为仿宋小四"""
    run.font.name = WORD_FONT_NAME
    run.font.size = Pt(WORD_FONT_SIZE)
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:eastAsia"), WORD_FONT_NAME)


def normalize_label(label):
    """标准化标签：去除空格和冒号"""
    return label.strip().rstrip("：:").strip()


def set_cell_text(cell, text):
    """设置单元格文字（仅用于简单文本，如周次/日期）"""
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run(text)
    apply_run_style(run)


def append_by_labels(cell, label_to_text, append_unmatched=True):
    """
    根据标签追加内容到单元格
    
    Args:
        cell: Word表格单元格
        label_to_text: {标签名: 内容} 字典
        append_unmatched: 是否添加未匹配的新标签
    """
    original_lines = cell.text.splitlines()
    if not original_lines:
        original_lines = [""]
    
    pending = {k: v for k, v in label_to_text.items() if v}
    matched = set()
    
    # 清空单元格
    cell.text = ""
    
    # 重建原有内容
    for i, line in enumerate(original_lines):
        if i == 0:
            p = cell.paragraphs[0]
        else:
            p = cell.add_paragraph()
        run = p.add_run(line)
        apply_run_style(run)
        
        # 检查该行是否匹配标签
        line_strip = line.strip()
        for label, extra in pending.items():
            if label in matched:
                continue
            
            label_norm = normalize_label(label)
            if label_norm and line_strip.startswith(label_norm):
                # 找到匹配的标签，创建新段落追加内容
                matched.add(label)
                
                # 按 \n 分段
                parts = extra.split('\n')
                for part in parts:
                    if part.strip():
                        new_p = cell.add_paragraph()
                        new_p.paragraph_format.first_line_indent = Pt(WORD_INDENT_FIRST_LINE)
                        run = new_p.add_run(part)
                        apply_run_style(run)
    
    # 添加未匹配的新标签
    if append_unmatched:
        for label, extra in pending.items():
            if label not in matched:
                # 创建标签行
                p = cell.add_paragraph()
                run = p.add_run(f"{label}：")
                apply_run_style(run)
                
                # 创建内容段落
                parts = extra.split('\n')
                for part in parts:
                    if part.strip():
                        new_p = cell.add_paragraph()
                        new_p.paragraph_format.first_line_indent = Pt(WORD_INDENT_FIRST_LINE)
                        run = new_p.add_run(part)
                        apply_run_style(run)


def flatten_plan_data(plan_data):
    """将嵌套的教案数据扁平化为 {字段: 值} 字典"""
    flat_data = {}
    for key, value in plan_data.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if sub_value:
                    flat_data[sub_key] = sub_value
        else:
            if value:
                flat_data[key] = value
    return flat_data


def fill_table_by_labels(table, label_to_text, content_col=1):
    """使用标签填充表格所有行的内容列"""
    for row in table.rows:
        if len(row.cells) <= content_col:
            continue
        append_by_labels(
            row.cells[content_col],
            label_to_text,
            append_unmatched=False,
        )


def fill_by_row_labels(table, label_to_text, label_col=0, content_col=1):
    """按行标签填充表格（标签在label_col，内容填入content_col）"""
    normalized_map = {
        normalize_label(label): text
        for label, text in label_to_text.items()
        if text
    }
    for row in table.rows:
        if len(row.cells) <= max(label_col, content_col):
            continue
        label_text = normalize_label(row.cells[label_col].text)
        if label_text and label_text in normalized_map:
            set_cell_text(row.cells[content_col], normalized_map[label_text])


def fill_doc_by_labels(
    doc,
    plan_data,
    week_text=None,
    date_text=None,
    content_col=1,
    label_col=0,
    header_table_index=0,
):
    """
    根据标签填充Word文档
    
    Args:
        doc: Document对象
        plan_data: 教案数据字典
        week_text: 周次文本
        date_text: 日期文本
        content_col: 内容列索引
        label_col: 标签列索引
        header_table_index: 包含周次/日期的表格索引
    """
    flat_data = flatten_plan_data(plan_data)
    for index, table in enumerate(doc.tables):
        fill_table_by_labels(table, flat_data, content_col=content_col)

        if index == header_table_index:
            if week_text is not None and len(table.rows) > 0:
                set_cell_text(table.cell(0, content_col), week_text)
            if date_text is not None and len(table.rows) > 1:
                set_cell_text(table.cell(1, content_col), date_text)

        fill_by_row_labels(
            table,
            flat_data,
            label_col=label_col,
            content_col=content_col,
        )


def fill_teacher_plan(doc, plan_data, week_text, date_text):
    """
    填充教师教案文档
    
    Args:
        doc: Document对象
        plan_data: 教案数据
        week_text: 周次文本（如"第（1）周"）
        date_text: 日期文本（如"周（一） 2月26日"）
    """
    fill_doc_by_labels(
        doc,
        plan_data,
        week_text=plan_data.get("周次", week_text),
        date_text=plan_data.get("日期", date_text),
        content_col=1,
        label_col=0,
        header_table_index=0,
    )


def generate_plan_docx(template_path, plan_data, week_text, date_text, output_path):
    """
    生成教案Word文档
    
    Args:
        template_path: 模板文档路径
        plan_data: 教案数据
        week_text: 周次
        date_text: 日期
        output_path: 输出文件路径
        
    Returns:
        输出文件路径 (Path对象)
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    doc = Document(template_path)
    fill_teacher_plan(doc, plan_data, week_text, date_text)
    doc.save(output_path)
    
    return output_path
