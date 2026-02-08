#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
幼儿园教案管理系统 - NiceGUI 前端
"""

import json
from pathlib import Path
from datetime import date
from nicegui import ui

from minimal_fill import (
    fill_teacher_plan,
    validate_plan_data,
    calculate_week_number,
    weekday_cn,
    build_sample_plan_data,
    FIELD_ORDER,
    SUBFIELDS,
)
from docx import Document


class TeacherPlanUI:
    def __init__(self):
        self.schema_path = Path("examples/plan_schema.json")
        self.template_path = Path("examples/teacherplan.docx")
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
        self.semester_start = None
        self.semester_end = None
        self.schema = None
        self.form_fields = {}
        
        self.load_schema()

    def load_schema(self):
        """加载字段 schema"""
        if not self.schema_path.exists():
            ui.notify("schema 文件不存在，请先运行 minimal_fill.py", position="top", type="negative")
            return
        
        with open(self.schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)

    def set_semester(self, start_date: str, end_date: str):
        """设置学期信息"""
        try:
            self.semester_start = date.fromisoformat(start_date)
            self.semester_end = date.fromisoformat(end_date)
            ui.notify(f"学期已设置：{start_date} 至 {end_date}", position="top", type="positive")
        except ValueError:
            ui.notify("日期格式错误，应为 YYYY-MM-DD", position="top", type="negative")

    def build_form(self):
        """根据 schema 动态生成表单"""
        if not self.schema:
            ui.notify("schema 未加载", position="top", type="negative")
            return
        
        self.form_fields.clear()

        with ui.column().classes("w-full"):
            ui.label("教案关键信息").classes("text-lg font-bold")
            
            with ui.row().classes("w-full gap-4"):
                with ui.input("学期开始日期").classes("w-48") as semester_start:
                    with semester_start.add_slot("append"):
                        ui.icon("event").on("click", lambda: semester_start_menu.open()).classes("cursor-pointer")
                    with ui.menu() as semester_start_menu:
                        semester_start_date = ui.date(value="2026-02-23").bind_value(semester_start)
                
                with ui.input("学期结束日期").classes("w-48") as semester_end:
                    with semester_end.add_slot("append"):
                        ui.icon("event").on("click", lambda: semester_end_menu.open()).classes("cursor-pointer")
                    with ui.menu() as semester_end_menu:
                        semester_end_date = ui.date(value="2026-07-10").bind_value(semester_end)
                
                with ui.input("教案日期").classes("w-48") as target_date:
                    with target_date.add_slot("append"):
                        ui.icon("event").on("click", lambda: target_date_menu.open()).classes("cursor-pointer")
                    with ui.menu() as target_date_menu:
                        target_date_picker = ui.date(value="2026-02-26").bind_value(target_date)
            
            def on_date_change():
                start = semester_start.value
                end = semester_end.value
                target = target_date.value
                if start and end and target:
                    self.set_semester(start, end)
                    try:
                        d = date.fromisoformat(target)
                        week_no = calculate_week_number(date.fromisoformat(start), d)
                        week_label.text = f"第（{week_no}）周"
                        day_label.text = f"周（{weekday_cn(d)}） {d.month}月{d.day}日"
                    except ValueError:
                        pass
            
            semester_start.on_value_change(on_date_change)
            semester_end.on_value_change(on_date_change)
            target_date.on_value_change(on_date_change)

            ui.separator()
            
            with ui.row().classes("w-full gap-4"):
                week_label = ui.label("第（0）周").classes("text-base font-semibold")
                day_label = ui.label("周（一） 2月26日").classes("text-base font-semibold")
            
            ui.separator()

            ui.label("教案详细内容").classes("text-lg font-bold")

            for field_info in self.schema["fields"]:
                field_name = field_info["name"]
                
                # 跳过周次和日期，已自动计算
                if field_name in ["周次", "日期"]:
                    continue
                
                required = field_info.get("required", False)
                required_marker = " *" if required else ""
                
                if field_info.get("type") == "group":
                    with ui.expansion(f"{field_name}{required_marker}").classes("w-full"):
                        subfields = field_info.get("subfields", [])
                        group_data = {}
                        
                        for subfield_info in subfields:
                            subfield_name = subfield_info["name"]
                            placeholder = subfield_info.get("placeholder", "")
                            
                            text_area = ui.textarea(
                                label=subfield_name,
                                placeholder=placeholder
                            ).classes("w-full")
                            group_data[subfield_name] = text_area
                        
                        self.form_fields[field_name] = group_data
                else:
                    text_area = ui.textarea(
                        label=f"{field_name}{required_marker}",
                        placeholder=field_info.get("placeholder", "")
                    ).classes("w-full")
                    self.form_fields[field_name] = text_area
            
            ui.separator()
            
            with ui.row().classes("w-full gap-4"):
                ui.button("生成教案", on_click=lambda: self.generate_plan(
                    semester_start.value,
                    semester_end.value,
                    target_date.value
                )).classes("bg-green-600 text-white")
                ui.button("填充测试数据", on_click=self.fill_sample_data).classes("bg-blue-600 text-white")
                ui.button("清空表单", on_click=self.clear_form).classes("bg-gray-600 text-white")

    def collect_plan_data(self):
        """收集表单数据"""
        plan_data = {}
        
        for field_name, field_widget in self.form_fields.items():
            if isinstance(field_widget, dict):
                group_data = {}
                for subfield_name, text_widget in field_widget.items():
                    group_data[subfield_name] = text_widget.value or ""
                plan_data[field_name] = group_data
            else:
                plan_data[field_name] = field_widget.value or ""
        
        return plan_data

    def generate_plan(self, start_date: str, end_date: str, target_date: str):
        """生成教案 Word"""
        try:
            if not self.template_path.exists():
                ui.notify(f"模板文件不存在：{self.template_path}", position="top", type="negative")
                return
            
            semester_start = date.fromisoformat(start_date)
            semester_end = date.fromisoformat(end_date)
            target = date.fromisoformat(target_date)
            
            if not (semester_start <= target <= semester_end):
                ui.notify("教案日期不在学期范围内", position="top", type="negative")
                return
            
            plan_data = self.collect_plan_data()
            
            errors = validate_plan_data(plan_data)
            if errors:
                ui.notify("\n".join(errors), position="top", type="negative")
                return
            
            week_no = calculate_week_number(semester_start, target)
            week_text = f"第（{week_no}）周"
            date_text = f"周（{weekday_cn(target)}） {target.month}月{target.day}日"
            
            doc = Document(self.template_path)
            fill_teacher_plan(doc, plan_data, week_text, date_text)
            
            output_file = self.output_dir / f"教案_{target.strftime('%Y%m%d')}.docx"
            doc.save(output_file)
            
            ui.notify(
                f"教案已生成：{output_file}",
                position="top",
                type="positive"
            )
        except ValueError as e:
            ui.notify(f"错误：{str(e)}", position="top", type="negative")
        except Exception as e:
            ui.notify(f"生成失败：{str(e)}", position="top", type="negative")

    def clear_form(self):
        """清空表单"""
        for field_widget in self.form_fields.values():
            if isinstance(field_widget, dict):
                for text_widget in field_widget.values():
                    text_widget.value = ""
            else:
                field_widget.value = ""
        ui.notify("表单已清空", position="top", type="info")

    def fill_sample_data(self):
        """填充测试数据"""
        sample_data = build_sample_plan_data()
        
        for field_name, field_widget in self.form_fields.items():
            sample_value = sample_data.get(field_name)
            if not sample_value:
                continue
                
            if isinstance(field_widget, dict):
                # 分组字段
                if isinstance(sample_value, dict):
                    for subfield_name, text_widget in field_widget.items():
                        text_widget.value = sample_value.get(subfield_name, "")
            else:
                # 单个字段
                field_widget.value = sample_value
        
        ui.notify("测试数据已填充", position="top", type="positive")


@ui.page("/")
def main_page():
    """主页面"""
    with ui.column().classes("w-full h-screen p-8 bg-gray-50"):
        ui.label("幼儿园教案管理系统").classes("text-3xl font-bold text-center")
        ui.label("电子备课系统").classes("text-base text-gray-600 text-center mb-6")
        
        with ui.card().classes("w-full"):
            plan_ui = TeacherPlanUI()
            plan_ui.build_form()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run()
