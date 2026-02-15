#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
幼儿园教案管理系统 - NiceGUI 前端
"""

import json
import asyncio
from pathlib import Path
from datetime import date, timedelta
from nicegui import ui
from docx import Document

import kg_manager as kg


class ConfigManager:
    """AI和数据库配置管理"""

    # LocalStorage 键
    STORAGE_PREFIX = "kg_manager_"
    AI_KEY = f"{STORAGE_PREFIX}ai_key"
    AI_MODEL = f"{STORAGE_PREFIX}ai_model"
    AI_BASE_URL = f"{STORAGE_PREFIX}ai_base_url"
    DB_TYPE = f"{STORAGE_PREFIX}db_type"
    MYSQL_HOST = f"{STORAGE_PREFIX}mysql_host"
    MYSQL_PORT = f"{STORAGE_PREFIX}mysql_port"
    MYSQL_DB = f"{STORAGE_PREFIX}mysql_db"
    MYSQL_USER = f"{STORAGE_PREFIX}mysql_user"
    MYSQL_PASSWORD = f"{STORAGE_PREFIX}mysql_password"

    @staticmethod
    async def get_config_from_storage():
        """从浏览器localStorage获取配置"""
        return {
            "ai_key": await ui.run_javascript(
                f"localStorage.getItem('{ConfigManager.AI_KEY}')"
            ),
            "ai_model": await ui.run_javascript(
                f"localStorage.getItem('{ConfigManager.AI_MODEL}')"
            ),
            "ai_base_url": await ui.run_javascript(
                f"localStorage.getItem('{ConfigManager.AI_BASE_URL}')"
            ),
            "db_type": await ui.run_javascript(
                f"localStorage.getItem('{ConfigManager.DB_TYPE}')"
            ),
            "mysql_config": {
                "host": await ui.run_javascript(
                    f"localStorage.getItem('{ConfigManager.MYSQL_HOST}')"
                ),
                "port": await ui.run_javascript(
                    f"localStorage.getItem('{ConfigManager.MYSQL_PORT}')"
                ),
                "db": await ui.run_javascript(
                    f"localStorage.getItem('{ConfigManager.MYSQL_DB}')"
                ),
                "user": await ui.run_javascript(
                    f"localStorage.getItem('{ConfigManager.MYSQL_USER}')"
                ),
                "password": await ui.run_javascript(
                    f"localStorage.getItem('{ConfigManager.MYSQL_PASSWORD}')"
                ),
            },
        }

    @staticmethod
    def save_to_storage(key, value):
        """保存配置到浏览器localStorage"""
        safe_key = json.dumps(str(key))
        safe_value = json.dumps("" if value is None else str(value))
        ui.run_javascript(f"localStorage.setItem({safe_key}, {safe_value})")


class TeacherPlanUI:
    def __init__(self):
        self.schema_path = Path("examples/plan_schema.json")
        self.template_path = Path("examples/teacherplan.docx")
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        self.semester_db_path = Path("examples/semester.db")
        self.plan_db_path = Path("examples/plan.db")
        kg.init_plan_db(self.plan_db_path)
        
        self.semester_start = None
        self.semester_end = None
        self.schema = None
        self.form_fields = {}
        self.plan_date_select = None
        self.collective_draft = None
        self.default_semester_start = "2026-02-23"
        self.default_semester_end = "2026-07-10"

        # AI配置
        self.ai_key = None
        self.ai_model = "gpt-4o-mini"
        self.ai_base_url = None
        
        # 数据库配置
        self.db_type = "sqlite"
        self.mysql_config = {
            "host": "",
            "port": 3306,
            "db": "",
            "user": "",
            "password": "",
        }

        latest_semester = kg.load_latest_semester(self.semester_db_path)
        if latest_semester:
            self.default_semester_start = latest_semester[0].isoformat()
            self.default_semester_end = latest_semester[1].isoformat()
        
        self.load_schema()

    def load_schema(self):
        """加载字段 schema"""
        if not self.schema_path.exists():
            msg = "schema 文件不存在，请先运行 minimal_fill.py"
            ui.notify(msg, position="top", type="negative")
            return
        
        with open(self.schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)

    def build_config_panel(self):
        """构建配置面板（AI和数据库配置）"""
        with ui.card().classes("w-full"):
            ui.label("系统配置").classes("text-2xl font-bold mb-4")
            
            # 标签页
            with ui.tabs().classes("w-full") as tabs:
                ai_tab = ui.tab("AI配置")
                db_tab = ui.tab("数据库配置")
            
            with ui.tab_panels(tabs).classes("w-full"):
                # AI配置标签页
                with ui.tab_panel(ai_tab):
                    with ui.column().classes("w-full gap-4"):
                        ui.label("OpenAI API 配置").classes(
                            "text-lg font-semibold"
                        )
                        
                        ai_key_input = ui.input(
                            label="API Key",
                            password=True,
                            placeholder="sk-..."
                        ).classes("w-full")
                        
                        ai_model_input = ui.input(
                            label="AI模型",
                            value=self.ai_model,
                            placeholder="gpt-4o-mini"
                        ).classes("w-full")
                        
                        ai_url_input = ui.input(
                            label="API地址 (可选)",
                            placeholder="https://api.openai.com/v1"
                        ).classes("w-full")
                        
                        # 异步加载配置并回填
                        async def load_ai_config():
                            config = (
                                await ConfigManager.get_config_from_storage()
                            )
                            if config.get("ai_key"):
                                ai_key_input.value = config["ai_key"]
                                self.ai_key = config["ai_key"]
                            if config.get("ai_model"):
                                ai_model_input.value = config["ai_model"]
                                self.ai_model = config["ai_model"]
                            if config.get("ai_base_url"):
                                ai_url_input.value = config["ai_base_url"]
                                self.ai_base_url = config["ai_base_url"]
                        
                        ui.timer(0.1, load_ai_config, once=True)
                        
                        def save_ai_config():
                            """保存AI配置"""
                            key = ai_key_input.value
                            model = ai_model_input.value
                            url = ai_url_input.value or None
                            
                            if not key:
                                ui.notify(
                                    "请输入 API Key",
                                    position="top",
                                    type="warning"
                                )
                                return
                            
                            self.ai_key = key
                            self.ai_model = model or "gpt-4o-mini"
                            self.ai_base_url = url
                            
                            # 保存到localStorage
                            ConfigManager.save_to_storage(
                                ConfigManager.AI_KEY, key
                            )
                            ConfigManager.save_to_storage(
                                ConfigManager.AI_MODEL, self.ai_model
                            )
                            if url:
                                ConfigManager.save_to_storage(
                                    ConfigManager.AI_BASE_URL, url
                                )
                            
                            ui.notify(
                                "AI配置已保存",
                                position="top",
                                type="positive"
                            )
                        
                        ui.button(
                            "保存配置",
                            on_click=save_ai_config
                        ).classes("bg-blue-600 text-white w-full")
                
                # 数据库配置标签页
                with ui.tab_panel(db_tab):
                    with ui.column().classes("w-full gap-4"):
                        ui.label("数据库选择").classes(
                            "text-lg font-semibold"
                        )
                        
                        db_type_select = ui.select(
                            label="数据库类型",
                            value=self.db_type,
                            options={
                                "sqlite": "SQLite (本地)",
                                "mysql": "MySQL (云部署)",
                            }
                        ).classes("w-full")
                        
                        # SQLite配置区域
                        sqlite_info = ui.html(
                            "<p class='text-sm text-gray-600'>"
                            "✓ SQLite: 使用本地数据库 "
                            "(examples/plan.db)</p>"
                        )
                        
                        # MySQL配置区域
                        mysql_panel = ui.column().classes("w-full gap-3")
                        with mysql_panel:
                            mysql_host = ui.input(
                                label="数据库地址",
                                placeholder="localhost"
                            ).classes("w-full")
                            
                            mysql_port = ui.input(
                                label="端口",
                                value="3306",
                                placeholder="3306"
                            ).classes("w-full")
                            
                            mysql_db = ui.input(
                                label="数据库名",
                                placeholder="kindergarten"
                            ).classes("w-full")
                            
                            mysql_user = ui.input(
                                label="用户名",
                                placeholder="root"
                            ).classes("w-full")
                            
                            mysql_password = ui.input(
                                label="密码",
                                password=True,
                                placeholder="password"
                            ).classes("w-full")
                        
                        # 异步加载配置并回填
                        async def load_db_config():
                            config = (
                                await ConfigManager.get_config_from_storage()
                            )
                            
                            # 加载数据库类型
                            db_type_val = config.get("db_type") or "sqlite"
                            self.db_type = db_type_val
                            db_type_select.value = db_type_val
                            mysql_panel.visible = (db_type_val == "mysql")
                            sqlite_info.visible = (db_type_val == "sqlite")
                            
                            # 加载MySQL配置
                            mysql_cfg = config.get("mysql_config", {})
                            if mysql_cfg.get("host"):
                                mysql_host.value = mysql_cfg["host"]
                                self.mysql_config["host"] = mysql_cfg["host"]
                            if mysql_cfg.get("port"):
                                mysql_port.value = str(mysql_cfg["port"])
                                try:
                                    port_val = int(mysql_cfg["port"])
                                    self.mysql_config["port"] = port_val
                                except (ValueError, TypeError):
                                    pass
                            if mysql_cfg.get("db"):
                                mysql_db.value = mysql_cfg["db"]
                                self.mysql_config["db"] = mysql_cfg["db"]
                            if mysql_cfg.get("user"):
                                mysql_user.value = mysql_cfg["user"]
                                self.mysql_config["user"] = mysql_cfg["user"]
                            if mysql_cfg.get("password"):
                                pwd = mysql_cfg["password"]
                                mysql_password.value = pwd
                                self.mysql_config["password"] = pwd
                        
                        ui.timer(0.1, load_db_config, once=True)
                        
                        # 默认隐藏MySQL配置
                        mysql_panel.visible = (self.db_type == "mysql")
                        sqlite_info.visible = (self.db_type == "sqlite")
                        
                        def on_db_type_change(new_db_type):
                            """切换数据库类型"""
                            self.db_type = new_db_type
                            mysql_panel.visible = (new_db_type == "mysql")
                            sqlite_info.visible = (new_db_type == "sqlite")
                            ConfigManager.save_to_storage(
                                ConfigManager.DB_TYPE, new_db_type
                            )
                        
                        db_type_select.on_value_change(
                            lambda e: on_db_type_change(e.value)
                        )
                        
                        def save_db_config():
                            """保存数据库配置"""
                            if self.db_type == "mysql":
                                if not all([
                                    mysql_host.value,
                                    mysql_db.value,
                                    mysql_user.value
                                ]):
                                    ui.notify(
                                        "请填写完整的MySQL配置",
                                        position="top",
                                        type="warning"
                                    )
                                    return
                                
                                self.mysql_config = {
                                    "host": mysql_host.value,
                                    "port": int(mysql_port.value or 3306),
                                    "db": mysql_db.value,
                                    "user": mysql_user.value,
                                    "password": mysql_password.value,
                                }
                                
                                # 保存到localStorage
                                ConfigManager.save_to_storage(
                                    ConfigManager.MYSQL_HOST,
                                    mysql_host.value
                                )
                                ConfigManager.save_to_storage(
                                    ConfigManager.MYSQL_PORT,
                                    str(self.mysql_config["port"])
                                )
                                ConfigManager.save_to_storage(
                                    ConfigManager.MYSQL_DB, mysql_db.value
                                )
                                ConfigManager.save_to_storage(
                                    ConfigManager.MYSQL_USER, mysql_user.value
                                )
                                ConfigManager.save_to_storage(
                                    ConfigManager.MYSQL_PASSWORD,
                                    mysql_password.value
                                )
                            
                            ui.notify(
                                f"{self.db_type.upper()} 配置已保存",
                                position="top",
                                type="positive"
                            )
                        
                        ui.button(
                            "保存配置",
                            on_click=save_db_config
                        ).classes("bg-green-600 text-white w-full")

    def set_semester(self, start_date: str, end_date: str):
        """设置学期信息"""
        try:
            self.semester_start = date.fromisoformat(start_date)
            self.semester_end = date.fromisoformat(end_date)
            msg = f"学期已设置：{start_date} 至 {end_date}"
            ui.notify(msg, position="top", type="positive")
        except ValueError:
            ui.notify("日期格式错误，应为 YYYY-MM-DD", position="top", type="negative")

    def save_semester_info(self, start_date: str, end_date: str):
        """保存学期信息到数据库"""
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
            kg.save_semester(self.semester_db_path, start, end)
            ui.notify("学期信息已保存", position="top", type="positive")
        except ValueError:
            ui.notify("日期格式错误，应为 YYYY-MM-DD", position="top", type="negative")

    def build_form(self):
        """根据 schema 动态生成表单"""
        if not self.schema:
            ui.notify("schema 未加载", position="top", type="negative")
            return
        
        self.form_fields.clear()

        with ui.column().classes("w-full"):
            # 添加配置面板（可折叠）
            with ui.expansion("⚙️ 系统配置").classes("w-full"):
                self.build_config_panel()
            
            ui.separator()

            with ui.row().classes("w-full gap-6"):
                with ui.column().classes("w-full md:w-1/2 gap-4"):
                    ui.label("数据库教案").classes("text-lg font-bold")
                    with ui.row().classes("w-full gap-4"):
                        self.plan_date_select = ui.select(
                            options=kg.list_plan_dates(self.plan_db_path),
                            label="已保存教案日期"
                        ).classes("w-48")
                        ui.button(
                            "加载到表单",
                            on_click=self.load_selected_plan
                        ).classes("bg-slate-600 text-white")
                        ui.button(
                            "导出选中日期",
                            on_click=self.export_selected_plan
                        ).classes("bg-teal-600 text-white")

                    with ui.row().classes("w-full gap-4"):
                        with ui.input("起始日期").classes("w-48") as range_start:
                            with range_start.add_slot("append"):
                                def open_range_menu():
                                    range_start_menu.open()
                                ui.icon("event").on(
                                    "click", open_range_menu
                                ).classes("cursor-pointer")
                            with ui.menu() as range_start_menu:
                                start_d = ui.date(
                                    value=self.default_semester_start
                                )
                                start_d.bind_value(range_start)

                        range_days = ui.number(
                            "连续天数",
                            value=1,
                            min=1
                        ).classes("w-32")
                        ui.button(
                            "连续导出",
                            on_click=lambda: self.export_range_plans(
                                range_start.value,
                                range_days.value
                            )
                        ).classes("bg-orange-600 text-white")

                    ui.separator()

                    ui.label("教案关键信息").classes("text-lg font-bold")

                    with ui.row().classes("w-full gap-4"):
                        with ui.input("学期开始日期").classes(
                            "w-48"
                        ) as semester_start:
                            with semester_start.add_slot("append"):
                                def open_start_menu():
                                    semester_start_menu.open()
                                ui.icon("event").on(
                                    "click", open_start_menu
                                ).classes("cursor-pointer")
                            with ui.menu() as semester_start_menu:
                                start_picker = ui.date(
                                    value=self.semester_start
                                )
                                start_picker.bind_value(semester_start)

                        with ui.input("学期结束日期").classes(
                            "w-48"
                        ) as semester_end:
                            with semester_end.add_slot("append"):
                                def open_end_menu():
                                    semester_end_menu.open()
                                ui.icon("event").on(
                                    "click", open_end_menu
                                ).classes("cursor-pointer")
                            with ui.menu() as semester_end_menu:
                                end_picker = ui.date(value=self.semester_end)
                                end_picker.bind_value(semester_end)

                        with ui.input("教案日期").classes("w-48") as target_date:
                            with target_date.add_slot("append"):
                                def open_date_menu():
                                    target_date_menu.open()
                                ui.icon("event").on(
                                    "click", open_date_menu
                                ).classes("cursor-pointer")
                            with ui.menu() as target_date_menu:
                                _ = ui.date(
                                    value="2026-02-26"
                                ).bind_value(target_date)

                        ui.button(
                            "保存学期",
                            on_click=lambda: self.save_semester_info(
                                semester_start.value,
                                semester_end.value,
                            )
                        ).classes("bg-blue-600 text-white")

                    def on_date_change():
                        start = semester_start.value
                        end = semester_end.value
                        target = target_date.value
                        if start and end and target:
                            self.set_semester(start, end)
                            try:
                                d = date.fromisoformat(target)
                                week_no = kg.calculate_week_number(
                                    date.fromisoformat(start), d
                                )
                                week_label.text = f"第（{week_no}）周"
                                day_label.text = (
                                    f"周（{kg.weekday_cn(d)}） "
                                    f"{d.month}月{d.day}日"
                                )
                            except ValueError:
                                pass

                    semester_start.on_value_change(on_date_change)
                    semester_end.on_value_change(on_date_change)
                    target_date.on_value_change(on_date_change)

                    with ui.row().classes("w-full gap-4"):
                        week_text = "第（0）周"
                        week_label = ui.label(week_text).classes(
                            "text-base font-semibold"
                        )
                        day_text = "周（一） 2月26日"
                        day_label = ui.label(day_text).classes(
                            "text-base font-semibold"
                        )

                    on_date_change()

                with ui.column().classes("w-full md:w-1/2 gap-4"):
                    ui.label("教案详细内容").classes("text-lg font-bold")

                    for field_info in self.schema["fields"]:
                        field_name = field_info["name"]

                        # 跳过周次和日期，已自动计算
                        if field_name in ["周次", "日期"]:
                            continue

                        required = field_info.get("required", False)
                        required_marker = " *" if required else ""

                        if field_info.get("type") == "group":
                            expansion_label = f"{field_name}{required_marker}"
                            with ui.expansion(expansion_label).classes(
                                "w-full"
                            ):
                                subfields = field_info.get("subfields", [])
                                group_data = {}

                                if field_name == "集体活动":
                                    self.collective_draft = ui.textarea(
                                        label="集体活动原稿",
                                        placeholder="粘贴完整原稿，AI 将自动拆分"
                                    ).classes("w-full")
                                    ui.button(
                                        "AI 拆分到集体活动",
                                        on_click=(
                                            self.ai_split_collective_activity
                                        )
                                    ).classes("bg-purple-600 text-white")

                                for subfield_info in subfields:
                                    subfield_name = subfield_info["name"]
                                    placeholder = subfield_info.get(
                                        "placeholder",
                                        ""
                                    )

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
                ui.button("导出为 Word", on_click=lambda: self.generate_plan(
                    semester_start.value,
                    semester_end.value,
                    target_date.value
                )).classes("bg-green-600 text-white")
                ui.button("保存到数据库", on_click=lambda: self.save_plan_to_db(
                    semester_start.value,
                    semester_end.value,
                    target_date.value
                )).classes("bg-emerald-600 text-white")
                ui.button(
                    "填充测试数据",
                    on_click=self.fill_sample_data
                ).classes("bg-blue-600 text-white")
                ui.button("清空表单", on_click=self.clear_form).classes(
                    "bg-gray-600 text-white"
                )

            ui.separator()

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

    def apply_plan_data(self, plan_data):
        """将数据回填到表单"""
        for field_name, field_widget in self.form_fields.items():
            value = plan_data.get(field_name)
            if isinstance(field_widget, dict):
                for subfield_name, text_widget in field_widget.items():
                    text_widget.value = ""
                if isinstance(value, dict):
                    for subfield_name, text_widget in field_widget.items():
                        text_widget.value = value.get(subfield_name, "")
            else:
                field_widget.value = value or ""

    def generate_plan(self, start_date: str, end_date: str, target_date: str):
        """生成教案 Word"""
        try:
            if not self.template_path.exists():
                ui.notify(
                    f"模板文件不存在：{self.template_path}",
                    position="top",
                    type="negative"
                )
                return
            
            semester_start = date.fromisoformat(start_date)
            semester_end = date.fromisoformat(end_date)
            target = date.fromisoformat(target_date)
            
            if not (semester_start <= target <= semester_end):
                ui.notify("教案日期不在学期范围内", position="top", type="negative")
                return
            
            plan_data = self.collect_plan_data()
            
            errors = kg.validate_plan_data(plan_data)
            if errors:
                ui.notify("\n".join(errors), position="top", type="negative")
                return
            
            week_no = kg.calculate_week_number(semester_start, target)
            week_text = f"第（{week_no}）周"
            date_text = f"周（{kg.weekday_cn(target)}） {target.month}月{target.day}日"
            
            doc = Document(self.template_path)
            kg.fill_teacher_plan(doc, plan_data, week_text, date_text)
            
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

    def save_plan_to_db(self, start_date: str, end_date: str, target_date: str):
        """保存教案到数据库"""
        try:
            semester_start = date.fromisoformat(start_date)
            semester_end = date.fromisoformat(end_date)
            target = date.fromisoformat(target_date)

            if not (semester_start <= target <= semester_end):
                ui.notify("教案日期不在学期范围内", position="top", type="negative")
                return

            plan_data = self.collect_plan_data()
            errors = kg.validate_plan_data(plan_data)
            if errors:
                ui.notify("\n".join(errors), position="top", type="negative")
                return

            kg.save_plan_data(self.plan_db_path, target.isoformat(), plan_data)
            self.refresh_plan_dates()
            ui.notify("教案已保存到数据库", position="top", type="positive")
        except ValueError:
            ui.notify("日期格式错误，应为 YYYY-MM-DD", position="top", type="negative")
        except Exception as e:
            ui.notify(f"保存失败：{str(e)}", position="top", type="negative")

    def export_plan_data(self, target: date, plan_data):
        week_no = kg.calculate_week_number(self.semester_start, target)
        week_text = f"第（{week_no}）周"
        date_text = f"周（{kg.weekday_cn(target)}） {target.month}月{target.day}日"

        doc = Document(self.template_path)
        kg.fill_teacher_plan(doc, plan_data, week_text, date_text)
        output_file = self.output_dir / f"教案_{target.strftime('%Y%m%d')}.docx"
        doc.save(output_file)
        return output_file

    def load_selected_plan(self):
        """加载数据库中选中的教案"""
        if not self.plan_date_select or not self.plan_date_select.value:
            ui.notify("请选择已保存的教案日期", position="top", type="negative")
            return
        plan_data = kg.load_plan_data(self.plan_db_path, self.plan_date_select.value)
        if not plan_data:
            ui.notify("未找到该日期的教案", position="top", type="negative")
            return
        self.apply_plan_data(plan_data)
        ui.notify("教案已加载到表单", position="top", type="positive")

    def export_selected_plan(self):
        """导出数据库中选中的教案"""
        if not self.plan_date_select or not self.plan_date_select.value:
            ui.notify("请选择已保存的教案日期", position="top", type="negative")
            return
        if not self.semester_start or not self.semester_end:
            ui.notify("请先设置学期信息", position="top", type="negative")
            return
        target = date.fromisoformat(self.plan_date_select.value)
        plan_data = kg.load_plan_data(self.plan_db_path, target.isoformat())
        if not plan_data:
            ui.notify("未找到该日期的教案", position="top", type="negative")
            return
        output_file = self.export_plan_data(target, plan_data)
        ui.notify(f"教案已导出：{output_file}", position="top", type="positive")

    def export_range_plans(self, start_date: str, days):
        """连续导出数据库中几天的教案"""
        if not self.semester_start or not self.semester_end:
            ui.notify("请先设置学期信息", position="top", type="negative")
            return
        try:
            start = date.fromisoformat(start_date)
            days = int(days)
        except ValueError:
            ui.notify("日期或天数格式错误", position="top", type="negative")
            return

        missing = []
        exported = []
        for offset in range(days):
            target = start + timedelta(days=offset)
            plan_data = kg.load_plan_data(self.plan_db_path, target.isoformat())
            if not plan_data:
                missing.append(target.isoformat())
                continue
            output_file = self.export_plan_data(target, plan_data)
            exported.append(output_file.name)

        if exported:
            ui.notify(f"已导出 {len(exported)} 份教案", position="top", type="positive")
        if missing:
            ui.notify(
                f"以下日期无数据：{', '.join(missing)}",
                position="top",
                type="warning"
            )

    def refresh_plan_dates(self):
        if self.plan_date_select:
            self.plan_date_select.options = kg.list_plan_dates(self.plan_db_path)

    async def ai_split_collective_activity(self):
        """AI 拆分集体活动原稿"""
        if not self.collective_draft or not self.collective_draft.value:
            ui.notify("请先填写集体活动原稿", position="top", type="negative")
            return
        
        if not self.ai_key:
            ui.notify(
                "请先在系统配置中设置 OpenAI API Key",
                position="top",
                type="warning"
            )
            return

        try:
            ui.notify("AI 正在处理，请稍候...", position="top", type="info")
            # 使用参数传递配置，避免修改全局环境变量
            payload = await asyncio.to_thread(
                kg.split_collective_activity,
                self.collective_draft.value,
                self.ai_key,
                self.ai_base_url,
                self.ai_model,
            )
            if not payload:
                ui.notify("AI 返回格式不正确", position="top", type="negative")
                return

            group = self.form_fields.get("集体活动", {})
            for key in [
                "活动主题", "活动目标", "活动准备",
                "活动重点", "活动难点", "活动过程"
            ]:
                if key in group and key in payload:
                    group[key].value = payload.get(key, "")
            ui.notify("AI 拆分完成", position="top", type="positive")
        except Exception as e:
            ui.notify(f"AI 处理失败：{str(e)}", position="top", type="negative")

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
        sample_data = kg.SAMPLE_PLAN_DATA
        
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
