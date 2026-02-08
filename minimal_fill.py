from pathlib import Path
from datetime import date, datetime
import json
import sqlite3

from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from chinese_calendar import is_workday


def apply_run_style(run):
    """设置字体为仿宋小四"""
    run.font.name = "FangSong"
    run.font.size = Pt(12)
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:eastAsia"), "仿宋")


def set_cell_text(cell, text):
    """设置单元格文字，仅用于周次/日期等简单文本"""
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run(text)
    apply_run_style(run)


def normalize_label(label):
    return label.strip().rstrip("：:").strip()


def append_by_labels(cell, label_to_text):
    """根据标签追加内容，新内容创建新段落并设置格式"""
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
                        new_p.paragraph_format.first_line_indent = Pt(24)
                        run = new_p.add_run(part)
                        apply_run_style(run)
    
    # 添加未匹配的新标签
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
                    new_p.paragraph_format.first_line_indent = Pt(24)
                    run = new_p.add_run(part)
                    apply_run_style(run)


def save_semester(db_path, start_date, end_date):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS semesters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO semesters (start_date, end_date, created_at) VALUES (?, ?, ?)",
            (start_date.isoformat(), end_date.isoformat(), datetime.now().isoformat(timespec="seconds")),
        )


def calculate_week_number(semester_start, target_date):
    delta_days = (target_date - semester_start).days
    return delta_days // 7 + 1


def weekday_cn(d):
    mapping = "一二三四五六日"
    return mapping[d.weekday()]


def build_sample_plan_data():
    return {
        "周次": "第（1）周",
        "日期": "周（一） 2月23日",
        "晨间活动": {
            "集体游戏": "捉迷藏",
            "自主游戏": "建构区自由搭建",
        },
        "晨间活动指导": {
            "重点指导": "规则意识与安全",
            "活动目标": "提升动作协调性",
            "指导要点": "控制速度、保持间距",
        },
        "晨间谈话": {
            "话题": "我喜欢的颜色",
            "问题设计": "你为什么喜欢这种颜色？",
        },
        "集体活动": {
            "活动主题": "小班美术《彩色雨点》",
            "活动目标": "体验点画，感受色彩变化",
            "活动准备": "彩笔、白纸、围裙",
            "活动重点": "掌握点画节奏",
            "活动难点": "颜色搭配",
            "活动过程": "导入-示范-操作-分享",
        },
        "室内区域游戏": {
            "游戏区域": "阅读区、建构区",
            "重点指导": "鼓励合作",
            "活动目标": "提升语言表达",
            "指导要点": "轮流表达、倾听他人",
            "支持策略": "提供图书卡片和积木",
        },
        "下午户外游戏": {
            "游戏区域": "操场接力区",
            "重点观察": "遵守规则",
            "活动目标": "提升协调与速度",
            "指导要点": "交接动作规范",
            "支持策略": "分组示范、同伴互评",
        },
        "一日活动反思": "幼儿参与度高，但个别幼儿注意力分散。",
    }


FIELD_ORDER = [
    ("周次", False),
    ("日期", False),
    ("晨间活动", True),
    ("晨间活动指导", True),
    ("晨间谈话", True),
    ("集体活动", True),
    ("室内区域游戏", True),
    ("下午户外游戏", True),
    ("一日活动反思", False),
]


SUBFIELDS = {
    "晨间活动": ["集体游戏", "自主游戏"],
    "晨间活动指导": ["重点指导", "活动目标", "指导要点"],
    "晨间谈话": ["话题", "问题设计"],
    "集体活动": ["活动主题", "活动目标", "活动准备", "活动重点", "活动难点", "活动过程"],
    "室内区域游戏": ["游戏区域", "重点指导", "活动目标", "指导要点", "支持策略"],
    "下午户外游戏": ["游戏区域", "重点观察", "活动目标", "指导要点", "支持策略"],
}


def validate_plan_data(plan_data):
    errors = []

    for field, required in FIELD_ORDER:
        if field in {"周次", "日期"}:
            continue
        value = plan_data.get(field)
        if required and not value:
            errors.append(f"缺少必填字段：{field}")
            continue
        if field in SUBFIELDS and value:
            if not isinstance(value, dict):
                errors.append(f"字段类型错误：{field} 需要字典")
                continue
            for subfield in SUBFIELDS[field]:
                if not value.get(subfield):
                    errors.append(f"缺少子字段：{field}.{subfield}")

    return errors


def export_schema_json(path):
    schema = {
        "fields": [
            {
                "name": name,
                "required": required,
                "type": "group" if name in SUBFIELDS else "text",
                "widget": "group" if name in SUBFIELDS else "textarea",
                "placeholder": f"请输入{name}",
                "subfields": [
                    {
                        "name": sub,
                        "type": "text",
                        "widget": "textarea",
                        "placeholder": f"请输入{sub}",
                    }
                    for sub in SUBFIELDS.get(name, [])
                ],
            }
            for name, required in FIELD_ORDER
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")


def fill_teacher_plan(doc, plan_data, week_text, date_text):
    table = doc.tables[0]

    set_cell_text(table.cell(0, 1), plan_data.get("周次", week_text))
    set_cell_text(table.cell(1, 1), plan_data.get("日期", date_text))

    append_by_labels(table.cell(2, 1), plan_data.get("晨间活动", {}))
    append_by_labels(table.cell(3, 1), plan_data.get("晨间活动指导", {}))
    append_by_labels(table.cell(4, 1), {"话题": plan_data.get("晨间谈话", {}).get("话题")})
    append_by_labels(table.cell(5, 1), {"问题设计": plan_data.get("晨间谈话", {}).get("问题设计")})

    append_by_labels(table.cell(6, 1), {"活动主题": plan_data.get("集体活动", {}).get("活动主题")})
    append_by_labels(table.cell(7, 1), {"活动目标": plan_data.get("集体活动", {}).get("活动目标")})
    append_by_labels(table.cell(8, 1), {"活动准备": plan_data.get("集体活动", {}).get("活动准备")})
    append_by_labels(table.cell(9, 1), {"活动重点": plan_data.get("集体活动", {}).get("活动重点")})
    append_by_labels(table.cell(10, 1), {"活动难点": plan_data.get("集体活动", {}).get("活动难点")})
    append_by_labels(table.cell(11, 1), {"活动过程": plan_data.get("集体活动", {}).get("活动过程")})

    append_by_labels(table.cell(12, 1), {"游戏区域": plan_data.get("室内区域游戏", {}).get("游戏区域")})
    append_by_labels(table.cell(13, 1), {
        "重点指导": plan_data.get("室内区域游戏", {}).get("重点指导"),
        "活动目标": plan_data.get("室内区域游戏", {}).get("活动目标"),
        "指导要点": plan_data.get("室内区域游戏", {}).get("指导要点"),
    })
    append_by_labels(table.cell(14, 1), {"支持策略": plan_data.get("室内区域游戏", {}).get("支持策略")})

    append_by_labels(table.cell(15, 1), {"游戏区域": plan_data.get("下午户外游戏", {}).get("游戏区域")})
    append_by_labels(table.cell(16, 1), {
        "重点观察": plan_data.get("下午户外游戏", {}).get("重点观察"),
        "活动目标": plan_data.get("下午户外游戏", {}).get("活动目标"),
        "指导要点": plan_data.get("下午户外游戏", {}).get("指导要点"),
    })
    append_by_labels(table.cell(17, 1), {"支持策略": plan_data.get("下午户外游戏", {}).get("支持策略")})

    reflection = plan_data.get("一日活动反思")
    if reflection:
        set_cell_text(table.cell(18, 1), reflection)


def main():
    src = Path("examples/teacherplan.docx")
    dst = Path("examples/teacherplan_filled.docx")
    db_path = Path("examples/semester.db")
    schema_path = Path("examples/plan_schema.json")

    semester_start = date.fromisoformat("2026-02-23")
    semester_end = date.fromisoformat("2026-07-10")
    target_date = date.fromisoformat("2026-02-26")

    if not (semester_start <= target_date <= semester_end):
        raise ValueError("target_date is out of semester range")

    save_semester(db_path, semester_start, semester_end)

    week_no = calculate_week_number(semester_start, target_date)
    week_text = f"第（{week_no}）周"
    date_text = f"周（{weekday_cn(target_date)}） {target_date.month}月{target_date.day}日"

    doc = Document(src)

    if not is_workday(target_date):
        print("Warning: target_date is not a workday in Chinese calendar.")

    plan_data = build_sample_plan_data()
    errors = validate_plan_data(plan_data)
    if errors:
        raise ValueError("; ".join(errors))
    fill_teacher_plan(doc, plan_data, week_text, date_text)

    export_schema_json(schema_path)
    print(f"Saved schema: {schema_path}")

    doc.save(dst)
    print(f"Saved: {dst}")


if __name__ == "__main__":
    main()
