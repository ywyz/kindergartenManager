"""Word 文档导出服务。

使用 python-docx 生成每日活动计划文档（单表格，8 行，2 列）。

表格结构：
  行1  第N周            （整行合并）
  行2  月 日 周X        （整行合并）
  行3  晨间活动     | 晨间活动内容
  行4  晨间谈话     | 谈话主题 + 问题设计
  行5  集体活动     | 活动目标/准备/重点/难点/过程（差异标红）
  行6  室内区域活动 | 游戏内容
  行7  户外游戏活动 | 游戏内容
  行8  一日活动反思 | （空白，用户手填）
"""
from io import BytesIO
from typing import Any

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from app.core.models.daily_plan import DailyPlan

_RED = RGBColor(0xFF, 0x00, 0x00)


def _set_font(
    run,
    size_pt: float = 11,
    bold: bool = False,
    color: RGBColor | None = None,
) -> None:
    """统一设置 run 字体（宋体）、字号、粗体与颜色。

    必须显式设置东亚字体属性，否则中文可能出现乱码。
    """
    run.font.name = "宋体"
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rFonts = rpr.get_or_add_rFonts()
    rFonts.set(qn("w:eastAsia"), "宋体")


def _write_cell(cell, text: str, size_pt: float = 11, bold: bool = False) -> None:
    """清空单元格，写入纯文本并应用字体样式。"""
    cell.text = text or ""
    for para in cell.paragraphs:
        for run in para.runs:
            _set_font(run, size_pt=size_pt, bold=bold)


def _merge_row(table, row_idx: int) -> None:
    """横向合并指定行的两列为一格。"""
    table.rows[row_idx].cells[0].merge(table.rows[row_idx].cells[1])


def _write_talk_cell(cell, daily_plan: DailyPlan) -> None:
    """填充晨间谈话单元格。

    若 morning_talk_questions 为空，则将 morning_talk_topic 作为完整文本
    直接写入（适用于 AI 一次性生成的合并文本）。
    否则分两段显示：谈话主题 + 问题设计。
    """
    cell.text = ""

    # 模式 A：合并文本（AI 生成，topic 存储完整内容，questions 为空）
    if daily_plan.morning_talk_topic and not daily_plan.morning_talk_questions:
        para = cell.paragraphs[0]
        _set_font(para.add_run(daily_plan.morning_talk_topic))
        return

    # 模式 B：分字段存储（旧数据兼容）
    first = True
    for prefix, content in [
        ("谈话主题：", daily_plan.morning_talk_topic),
        ("问题设计：", daily_plan.morning_talk_questions),
    ]:
        if not content:
            continue
        if first:
            para = cell.paragraphs[0]
            first = False
        else:
            para = cell.add_paragraph()
        _set_font(para.add_run(f"{prefix}{content}"))


def _build_collective_cell(
    cell,
    daily_plan: DailyPlan,
    diff_result: list[dict],
) -> None:
    """填充集体活动单元格，活动过程按差异结果标红。

    Args:
        cell: 目标单元格。
        daily_plan: 教案数据对象。
        diff_result: 差异列表，格式 [{"text": str, "changed": bool}]。
    """
    cell.text = ""
    used_first = False

    def _para() -> Any:
        nonlocal used_first
        if not used_first:
            used_first = True
            return cell.paragraphs[0]
        return cell.add_paragraph()

    # 逐字段填充（有内容才写入）
    for label, value in [
        ("活动目标", daily_plan.activity_goal),
        ("活动准备", daily_plan.activity_prep),
        ("活动重点", daily_plan.activity_key),
        ("活动难点", daily_plan.activity_difficult),
    ]:
        if value:
            p = _para()
            _set_font(p.add_run(f"{label}："), bold=True)
            _set_font(p.add_run(value))

    # 活动过程：优先使用 diff_result 标红，无 diff 时直接输出改写文
    has_adapted = bool(daily_plan.activity_process_adapted)
    if diff_result or has_adapted:
        p = _para()
        _set_font(p.add_run("活动过程："), bold=True)
        if diff_result:
            for item in diff_result:
                color = _RED if item.get("changed") else None
                _set_font(p.add_run(item["text"]), color=color)
        elif has_adapted:
            _set_font(p.add_run(daily_plan.activity_process_adapted or ""))


def export_daily_plan(daily_plan: DailyPlan, diff_result: list[dict]) -> bytes:
    """生成每日活动计划 Word 文档，返回文档字节流。

    Args:
        daily_plan: 数据库中查询到的 DailyPlan 对象。
        diff_result: 由 diff_service.compute_diff() 计算的差异列表，
                     格式 [{"text": str, "changed": bool}]。
                     changed=True 的句子在导出文档中以红色字体显示。

    Returns:
        Word 文档的 bytes 内容（不写磁盘，由调用方决定存储方式）。
    """
    doc = Document()

    # 删除 Document() 创建时自动生成的空段落
    for para in list(doc.paragraphs):
        para._element.getparent().remove(para._element)

    # 创建 2 列 8 行表格，使用内置表格网格样式
    table = doc.add_table(rows=8, cols=2)
    table.style = "Table Grid"

    # ── 行 1：第N周（整行合并）
    _merge_row(table, 0)
    week_text = f"第 {daily_plan.week_number} 周" if daily_plan.week_number else "第 — 周"
    _write_cell(table.rows[0].cells[0], week_text, size_pt=14, bold=True)

    # ── 行 2：月 日 周X（整行合并）
    _merge_row(table, 1)
    d = daily_plan.plan_date
    date_text = f"{d.month} 月 {d.day} 日  {daily_plan.weekday_cn}" if d else ""
    _write_cell(table.rows[1].cells[0], date_text, size_pt=12, bold=True)

    # ── 行 3：晨间活动
    _write_cell(table.rows[2].cells[0], "晨间活动", bold=True)
    _write_cell(table.rows[2].cells[1], daily_plan.morning_activity or "")

    # ── 行 4：晨间谈话
    _write_cell(table.rows[3].cells[0], "晨间谈话", bold=True)
    _write_talk_cell(table.rows[3].cells[1], daily_plan)

    # ── 行 5：集体活动（含差异标注的活动过程）
    _write_cell(table.rows[4].cells[0], "集体活动", bold=True)
    _build_collective_cell(table.rows[4].cells[1], daily_plan, diff_result)

    # ── 行 6：室内区域活动
    _write_cell(table.rows[5].cells[0], "室内区域活动", bold=True)
    _write_cell(table.rows[5].cells[1], daily_plan.indoor_area or "")

    # ── 行 7：户外游戏活动
    _write_cell(table.rows[6].cells[0], "户外游戏活动", bold=True)
    _write_cell(table.rows[6].cells[1], daily_plan.outdoor_activity or "")

    # ── 行 8：一日活动反思（留空白，用户手填）
    _write_cell(table.rows[7].cells[0], "一日活动反思", bold=True)
    _write_cell(table.rows[7].cells[1], daily_plan.daily_reflection or "")

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
