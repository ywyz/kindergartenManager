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
    AI_GRADE_LEVEL = f"{STORAGE_PREFIX}ai_grade_level"
    AI_CLASS_ZONES = f"{STORAGE_PREFIX}ai_class_zones"
    AI_OUTDOOR_ZONES = f"{STORAGE_PREFIX}ai_outdoor_zones"
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
            "ai_grade_level": await ui.run_javascript(
                f"localStorage.getItem('{ConfigManager.AI_GRADE_LEVEL}')"
            ),
            "ai_class_zones": await ui.run_javascript(
                f"localStorage.getItem('{ConfigManager.AI_CLASS_ZONES}')"
            ),
            "ai_outdoor_zones": await ui.run_javascript(
                f"localStorage.getItem('{ConfigManager.AI_OUTDOOR_ZONES}')"
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
    async def save_to_storage(key, value):
        """保存配置到浏览器localStorage"""
        safe_key = json.dumps(str(key))
        safe_value = json.dumps("" if value is None else str(value))
        await ui.run_javascript(
            f"localStorage.setItem({safe_key}, {safe_value})"
        )


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
        self.ai_grade_level = ""
        self.ai_class_zones = ""
        self.ai_outdoor_zones = ""
        self.ai_context_labels = {}
        
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

                        ai_grade_input = ui.input(
                            label="幼儿园年级段",
                            placeholder="小班/中班/大班"
                        ).classes("w-full")

                        ai_class_zones_input = ui.input(
                            label="班级提供区域",
                            placeholder="如：角色区、建构区、阅读区"
                        ).classes("w-full")

                        ai_outdoor_zones_input = ui.input(
                            label="幼儿园户外区域",
                            placeholder="如：沙水区、平衡区、草地"
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
                            if config.get("ai_grade_level"):
                                ai_grade_input.value = config["ai_grade_level"]
                                self.ai_grade_level = config["ai_grade_level"]
                            if config.get("ai_class_zones"):
                                ai_class_zones = config["ai_class_zones"]
                                ai_class_zones_input.value = ai_class_zones
                                self.ai_class_zones = ai_class_zones
                            if config.get("ai_outdoor_zones"):
                                ai_outdoor_zones = config["ai_outdoor_zones"]
                                ai_outdoor_zones_input.value = ai_outdoor_zones
                                self.ai_outdoor_zones = ai_outdoor_zones
                        
                        ui.timer(0.1, load_ai_config, once=True)
                        
                        async def save_ai_config():
                            """保存AI配置"""
                            key = ai_key_input.value
                            model = ai_model_input.value
                            url = ai_url_input.value or None
                            grade_level = ai_grade_input.value or ""
                            class_zones = ai_class_zones_input.value or ""
                            outdoor_zones = ai_outdoor_zones_input.value or ""
                            
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
                            self.ai_grade_level = grade_level
                            self.ai_class_zones = class_zones
                            self.ai_outdoor_zones = outdoor_zones
                            
                            # 保存到localStorage
                            await ConfigManager.save_to_storage(
                                ConfigManager.AI_KEY, key
                            )
                            await ConfigManager.save_to_storage(
                                ConfigManager.AI_MODEL, self.ai_model
                            )
                            if url:
                                await ConfigManager.save_to_storage(
                                    ConfigManager.AI_BASE_URL, url
                                )
                            await ConfigManager.save_to_storage(
                                ConfigManager.AI_GRADE_LEVEL, grade_level
                            )
                            await ConfigManager.save_to_storage(
                                ConfigManager.AI_CLASS_ZONES, class_zones
                            )
                            await ConfigManager.save_to_storage(
                                ConfigManager.AI_OUTDOOR_ZONES, outdoor_zones
                            )

                            self.update_ai_context_labels()
                            
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
                        
                        async def on_db_type_change(new_db_type):
                            """切换数据库类型"""
                            self.db_type = new_db_type
                            mysql_panel.visible = (new_db_type == "mysql")
                            sqlite_info.visible = (new_db_type == "sqlite")
                            await ConfigManager.save_to_storage(
                                ConfigManager.DB_TYPE, new_db_type
                            )
                        
                        db_type_select.on_value_change(
                            lambda e: asyncio.create_task(
                                on_db_type_change(e.value)
                            )
                        )
                        
                        async def save_db_config():
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
                                await ConfigManager.save_to_storage(
                                    ConfigManager.MYSQL_HOST,
                                    mysql_host.value
                                )
                                await ConfigManager.save_to_storage(
                                    ConfigManager.MYSQL_PORT,
                                    str(self.mysql_config["port"])
                                )
                                await ConfigManager.save_to_storage(
                                    ConfigManager.MYSQL_DB, mysql_db.value
                                )
                                await ConfigManager.save_to_storage(
                                    ConfigManager.MYSQL_USER, mysql_user.value
                                )
                                await ConfigManager.save_to_storage(
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

                    # AI 快速填充区域
                    with ui.expansion("🤖 AI 快速填充").classes("w-full"):
                        ui.label("自动生成除集体活动外的所有内容").classes(
                            "text-sm text-gray-600"
                        )

                        ai_debug_output = ui.textarea(
                            label="AI 返回数据（调试）",
                            placeholder="显示 AI 返回的原始 JSON 数据",
                        ).classes("w-full text-xs").props("rows=6, readonly")

                        async def quick_ai_fill():
                            config = (
                                await ConfigManager.get_config_from_storage()
                            )
                            api_key = config.get("ai_key")
                            model = config.get("ai_model") or "gpt-4o-mini"
                            base_url = config.get("ai_base_url")

                            if not api_key:
                                ui.notify(
                                    "请先在系统配置中设置 OpenAI API Key",
                                    position="top",
                                    type="warning",
                                )
                                return

                            try:
                                # 获取背景信息构建输入
                                grade = self.ai_grade_level or "小班"
                                class_zones = (
                                    self.ai_class_zones or "角色区、建构区"
                                )
                                outdoor_zones = (
                                    self.ai_outdoor_zones or "操场、沙水区"
                                )
                                
                                # 动态生成提示词，明确指定要生成的字段
                                system_prompt = (
                                    f"你是幼儿园教案专家。基于以下信息生成教案内容。\n"
                                    f"【背景信息】\n"
                                    f"- 年级段：{grade}\n"
                                    f"- 班级区域：{class_zones}\n"
                                    f"- 户外区域：{outdoor_zones}\n\n"
                                    f"【生成要求】\n"
                                    f"生成以下字段（不包括集体活动和一日活动反思）：\n"
                                    f"1. 晨间活动（包含：集体游戏、自主游戏、重点指导、活动目标、指导要点）\n"
                                    f"2. 晨间谈话（包含：话题、问题设计）\n"
                                    f"3. 室内区域游戏"
                                    f"（包含：游戏区域、重点指导、活动目标、指导要点、支持策略）\n"
                                    f"4. 下午户外游戏"
                                    f"（包含：游戏区域、重点观察、活动目标、指导要点、支持策略）\n\n"
                                    f"【输出格式】\n"
                                    f"必须返回严格的JSON格式，不要包含任何其他文字。"
                                    f"包含所有上述字段及其子字段。\n"
                                    f"示例结构：\n"
                                    f'{{\n'
                                    f'  "晨间活动": {{\n'
                                    f'    "集体游戏": "...",\n'
                                    f'    "自主游戏": "...",\n'
                                    f'    "重点指导": "...",\n'
                                    f'    "活动目标": "...",\n'
                                    f'    "指导要点": "..."\n'
                                    f'  }},\n'
                                    f'  "晨间谈话": {{\n'
                                    f'    "话题": "...",\n'
                                    f'    "问题设计": "..."\n'
                                    f'  }},\n'
                                    f'  "室内区域游戏": {{\n'
                                    f'    "游戏区域": "...",\n'
                                    f'    "重点指导": "...",\n'
                                    f'    "活动目标": "...",\n'
                                    f'    "指导要点": "...",\n'
                                    f'    "支持策略": "..."\n'
                                    f'  }},\n'
                                    f'  "下午户外游戏": {{\n'
                                    f'    "游戏区域": "...",\n'
                                    f'    "重点观察": "...",\n'
                                    f'    "活动目标": "...",\n'
                                    f'    "指导要点": "...",\n'
                                    f'    "支持策略": "..."\n'
                                    f'  }}\n'
                                    f'}}\n'
                                )
                                
                                input_context = (
                                    f"年级段：{grade}\n"
                                    f"班级区域：{class_zones}\n"
                                    f"户外区域：{outdoor_zones}\n"
                                    f"请根据以上信息生成教案内容"
                                )

                                ui.notify(
                                    "AI 正在生成，请稍候...",
                                    position="top",
                                    type="info",
                                )

                                payload = await asyncio.to_thread(
                                    kg.run_ai_json_task,
                                    input_context,
                                    api_key,
                                    base_url,
                                    model,
                                    system_prompt,
                                )

                                # 显示调试信息
                                ai_debug_output.value = json.dumps(
                                    payload,
                                    ensure_ascii=False,
                                    indent=2,
                                )

                                # 自动填充表单
                                # （排除集体活动和一日活动反思）
                                skip_fields = {
                                    "集体活动",
                                    "一日活动反思",
                                }
                                filled_count = 0
                                fill_debug = []
                                
                                # 调试：显示当前表单字段
                                fill_debug.append(
                                    f"表单字段：{list(self.form_fields.keys())}"
                                )
                                fill_debug.append(
                                    f"AI 返回字段：{list(payload.keys())}"
                                )
                                
                                for field_name, value in payload.items():
                                    if field_name in skip_fields:
                                        fill_debug.append(
                                            f"跳过字段：{field_name}"
                                        )
                                        continue
                                    
                                    fill_debug.append(
                                        f"处理字段：{field_name}, "
                                        f"类型：{type(value).__name__}"
                                    )
                                    
                                    if field_name not in self.form_fields:
                                        fill_debug.append(
                                            "  字段不存在于表单"
                                        )
                                        continue
                                    
                                    field_widget = (
                                        self.form_fields[field_name]
                                    )
                                    
                                    if isinstance(value, dict):
                                        # 分组字段
                                        fill_debug.append(
                                            f"  -> 分组字段，子字段："
                                            f"{list(value.keys())}"
                                        )
                                        if isinstance(field_widget, dict):
                                            fill_debug.append(
                                                f"     表单子字段："
                                                f"{list(field_widget.keys())}"
                                            )
                                            for (
                                                sub_key,
                                                sub_val,
                                            ) in value.items():
                                                if (
                                                    sub_key in field_widget
                                                ):
                                                    field_widget[
                                                        sub_key
                                                    ].value = str(sub_val)
                                                    filled_count += 1
                                                    fill_debug.append(
                                                        f"     填充"
                                                        f"{sub_key}"
                                                    )
                                                else:
                                                    fill_debug.append(
                                                        f"     子字段"
                                                        f"{sub_key}"
                                                        "不存在"
                                                    )
                                        else:
                                            fill_debug.append(
                                                "     表单字段不是字典"
                                            )
                                    else:
                                        # 普通字段
                                        if isinstance(field_widget, dict):
                                            fill_debug.append(
                                                "  表单是分组，"
                                                "但 AI 返回普通值"
                                            )
                                        else:
                                            field_widget.value = (
                                                str(value)
                                            )
                                            filled_count += 1
                                            fill_debug.append(
                                                "  填充普通字段"
                                            )
                                
                                # 显示填充调试信息
                                ai_debug_output.value = (
                                    "\n".join(fill_debug) +
                                    "\n\n=== AI 返回数据 ===\n" +
                                    json.dumps(
                                        payload,
                                        ensure_ascii=False,
                                        indent=2,
                                    )
                                )

                                ui.notify(
                                    f"AI 生成完成，"
                                    f"填充了 {filled_count} 个字段",
                                    position="top",
                                    type="positive",
                                )
                            except Exception as e:
                                ai_debug_output.value = f"错误: {str(e)}"
                                ui.notify(
                                    f"AI 处理失败：{str(e)}",
                                    position="top",
                                    type="negative",
                                )

                        ui.button(
                            "AI 一键生成",
                            on_click=quick_ai_fill,
                        ).classes("w-full bg-purple-600 text-white")

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

                                    with ui.column().classes(
                                        "w-full gap-1 bg-gray-50 p-3 rounded"
                                    ):
                                        ui.label("AI 背景信息").classes(
                                            "text-sm font-semibold text-gray-600"
                                        )
                                        self.ai_context_labels = {
                                            "grade": ui.label().classes(
                                                "text-sm text-gray-600"
                                            ),
                                            "class_zones": ui.label().classes(
                                                "text-sm text-gray-600"
                                            ),
                                            "outdoor_zones": ui.label().classes(
                                                "text-sm text-gray-600"
                                            ),
                                        }
                                    self.update_ai_context_labels()
                                    ui.timer(
                                        0.2,
                                        self.update_ai_context_labels,
                                        once=True,
                                    )

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
                async def load_ai_output_from_storage():
                    """从localStorage读取AI输出并填充表单"""
                    ai_output = await ui.run_javascript(
                        "localStorage.getItem('kg_manager_ai_output')"
                    )
                    if not ai_output:
                        ui.notify(
                            "没有保存的AI输出，请先运行AI工具",
                            position="top",
                            type="warning",
                        )
                        return
                    try:
                        data = json.loads(ai_output)
                        
                        # 将AI输出数据合并到plan_data
                        for key, value in data.items():
                            if key in self.form_fields:
                                if isinstance(value, dict):
                                    # 处理分组字段
                                    for sub_key, sub_val in value.items():
                                        if (
                                            key in self.form_fields and
                                            sub_key in self.form_fields[key]
                                        ):
                                            field_widget = (
                                                self.form_fields[key][sub_key]
                                            )
                                            field_widget.value = sub_val
                                else:
                                    # 处理普通字段
                                    self.form_fields[key].value = value
                        
                        ui.notify(
                            "AI输出已填充到表单",
                            position="top",
                            type="positive",
                        )
                    except json.JSONDecodeError:
                        ui.notify(
                            "AI输出格式错误",
                            position="top",
                            type="negative",
                        )
                
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
                    "从AI工具填充",
                    on_click=load_ai_output_from_storage,
                ).classes("bg-orange-600 text-white")
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
            system_prompt = self.build_collective_activity_prompt()
            payload = await asyncio.to_thread(
                kg.split_collective_activity,
                self.collective_draft.value,
                self.ai_key,
                self.ai_base_url,
                self.ai_model,
                system_prompt,
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

    def update_ai_context_labels(self):
        """刷新AI背景信息展示"""
        labels = self.ai_context_labels
        if not labels:
            return

        grade = self.ai_grade_level or "未设置"
        class_zones = self.ai_class_zones or "未设置"
        outdoor_zones = self.ai_outdoor_zones or "未设置"

        labels["grade"].text = f"年级段：{grade}"
        labels["class_zones"].text = f"班级区域：{class_zones}"
        labels["outdoor_zones"].text = f"户外区域：{outdoor_zones}"

    def build_collective_activity_prompt(self):
        """构建集体活动拆分提示词"""
        context_lines = []
        if self.ai_grade_level:
            context_lines.append(f"年级段：{self.ai_grade_level}")
        if self.ai_class_zones:
            context_lines.append(f"班级区域：{self.ai_class_zones}")
        if self.ai_outdoor_zones:
            context_lines.append(f"户外区域：{self.ai_outdoor_zones}")

        prompt = (
            "你是幼儿园教案助理。请将用户提供的集体活动原稿拆分为固定字段："
            "活动主题、活动目标、活动准备、活动重点、活动难点、活动过程。"
            "请只输出 JSON 对象，不要包含多余文字或 Markdown。"
            "输出示例："
            "{"
            '"活动主题":"...",'
            '"活动目标":"...",'
            '"活动准备":"...",'
            '"活动重点":"...",'
            '"活动难点":"...",'
            '"活动过程":"..."'
            "}"
        )

        if context_lines:
            context_text = "\n".join(context_lines)
            prompt = f"{prompt}\n可用背景信息：\n{context_text}"

        return prompt

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
        ui.link("AI 工具", "/ai").classes("text-sm text-blue-600 text-center")
        
        with ui.card().classes("w-full"):
            plan_ui = TeacherPlanUI()
            plan_ui.build_form()


@ui.page("/ai")
def ai_tool_page():
    """独立AI工具页面"""
    with ui.column().classes("w-full min-h-screen p-8 bg-gray-50 gap-4"):
        ui.label("AI 工具").classes("text-3xl font-bold text-center")
        ui.link("返回主页面", "/").classes("text-sm text-blue-600 text-center")

        schema_fields = [
            name for name, _ in kg.FIELD_ORDER
            if name not in ["周次", "日期"]
        ]
        
        # AI页面中合并"晨间活动"和"晨间活动指导"
        ai_display_fields = [
            f for f in schema_fields if f != "晨间活动指导"
        ]
        # 添加合并标记
        merged_field_map = {
            "晨间活动": "晨间活动 + 晨间活动指导",
        }

        with ui.card().classes("w-full"):
            ui.label("提示词与输入").classes("text-lg font-semibold")

            prompt_input = ui.textarea(
                label="系统提示词",
                placeholder="在此编辑或生成提示词"
            ).classes("w-full")

            field_checks = {}
            output_fields_preview = ui.textarea(
                label="输出字段（已选）",
                placeholder="请选择教案字段",
            ).classes("w-full").props("readonly")

            def build_output_structure(selected_fields):
                output = {}
                for field_name in selected_fields:
                    # 晨间活动合并处理
                    if field_name == "晨间活动":
                        output["晨间活动"] = {
                            sub: "..." for sub in kg.SUBFIELDS.get(
                                "晨间活动", []
                            )
                        }
                        output["晨间活动指导"] = {
                            sub: "..." for sub in kg.SUBFIELDS.get(
                                "晨间活动指导", []
                            )
                        }
                    elif field_name in kg.SUBFIELDS:
                        output[field_name] = {
                            sub: "..." for sub in kg.SUBFIELDS[field_name]
                        }
                    else:
                        output[field_name] = "..."
                return output

            def update_output_fields_preview():
                fields = [
                    name for name, checkbox in field_checks.items()
                    if checkbox.value
                ]
                output_fields_preview.value = json.dumps(
                    build_output_structure(fields),
                    ensure_ascii=False,
                    indent=2,
                )
            with ui.column().classes("w-full gap-2"):
                ui.label("教案字段选项（可多选）").classes(
                    "text-sm font-semibold text-gray-600"
                )
                for field_name in ai_display_fields:
                    checkbox = ui.checkbox(
                        merged_field_map.get(field_name, field_name)
                    )
                    checkbox.on_value_change(
                        lambda e: update_output_fields_preview()
                    )
                    field_checks[field_name] = checkbox
                    if field_name == "晨间活动":
                        # 晨间活动合并显示子字段
                        morning_subfields = (
                            kg.SUBFIELDS.get("晨间活动", []) +
                            kg.SUBFIELDS.get("晨间活动指导", [])
                        )
                        ui.label(
                            "子字段：" + "、".join(morning_subfields)
                        ).classes("text-xs text-gray-500 ml-6")
                    elif field_name in kg.SUBFIELDS:
                        ui.label(
                            "子字段：" + "、".join(kg.SUBFIELDS[field_name])
                        ).classes("text-xs text-gray-500 ml-6")

            input_text = ui.textarea(
                label="输入内容",
                placeholder="粘贴原稿或需求描述"
            ).classes("w-full")

            output_text = ui.textarea(
                label="AI 输出（JSON）",
                placeholder="AI 返回结果将显示在这里"
            ).classes("w-full").props("readonly")

            async def load_ai_prompt():
                template = await asyncio.to_thread(
                    kg.load_ai_prompt_template,
                    Path("examples/plan.db"),
                    "default",
                )
                if template:
                    prompt_input.value = template.get("prompt_text", "")
                    selected = set(template.get("selected_fields", []))
                    for name, checkbox in field_checks.items():
                        checkbox.value = (name in selected)
                    update_output_fields_preview()
                    return

                prompt = await asyncio.to_thread(
                    kg.load_ai_prompt,
                    Path("examples/plan.db"),
                )
                if prompt:
                    prompt_input.value = prompt
                    update_output_fields_preview()

            ui.timer(0.1, load_ai_prompt, once=True)

            def build_prompt_from_fields():
                fields = [
                    name for name, checkbox in field_checks.items()
                    if checkbox.value
                ]
                if not fields:
                    ui.notify("请先填写输出字段", position="top", type="warning")
                    return
                example = json.dumps(
                    build_output_structure(fields),
                    ensure_ascii=False,
                    indent=2,
                )
                prompt_input.value = (
                    "你是幼儿园教案助理。请根据用户输入生成 JSON 输出。"
                    "按字段输出，其中包含子字段的需输出为对象结构。"
                    "请只输出 JSON 对象，不要包含多余文字或 Markdown。"
                    "输出示例：\n" + example
                )

            async def save_prompt():
                await asyncio.to_thread(
                    kg.save_ai_prompt_template,
                    Path("examples/plan.db"),
                    "default",
                    {
                        "prompt_text": prompt_input.value or "",
                        "selected_fields": [
                            name for name, checkbox in field_checks.items()
                            if checkbox.value
                        ],
                    },
                )
                ui.notify("提示词已保存到本地数据库", position="top", type="positive")

            async def run_ai_task():
                config = await ConfigManager.get_config_from_storage()
                api_key = config.get("ai_key")
                model = config.get("ai_model") or "gpt-4o-mini"
                base_url = config.get("ai_base_url")
                prompt = prompt_input.value or ""
                user_text = input_text.value or ""

                if not api_key:
                    ui.notify(
                        "请先在系统配置中设置 OpenAI API Key",
                        position="top",
                        type="warning",
                    )
                    return
                if not prompt.strip():
                    ui.notify(
                        "请先填写系统提示词",
                        position="top",
                        type="warning",
                    )
                    return
                if not user_text.strip():
                    ui.notify("请输入内容", position="top", type="warning")
                    return

                try:
                    ui.notify(
                        "AI 正在处理，请稍候...",
                        position="top",
                        type="info",
                    )
                    payload = await asyncio.to_thread(
                        kg.run_ai_json_task,
                        user_text,
                        api_key,
                        base_url,
                        model,
                        prompt,
                    )
                    output_text.value = json.dumps(
                        payload,
                        ensure_ascii=False,
                        indent=2,
                    )
                    ui.notify("AI 处理完成", position="top", type="positive")
                except Exception as e:
                    ui.notify(
                        f"AI 处理失败：{str(e)}",
                        position="top",
                        type="negative",
                    )

            async def save_ai_output_to_storage():
                """将AI输出保存到localStorage供主表单使用"""
                if not output_text.value or not output_text.value.strip():
                    ui.notify(
                        "请先运行AI生成",
                        position="top",
                        type="warning",
                    )
                    return
                try:
                    await ConfigManager.save_to_storage(
                        "kg_manager_ai_output",
                        output_text.value,
                    )
                    ui.notify(
                        "AI输出已保存，请返回主页面填充表单",
                        position="top",
                        type="positive",
                    )
                except Exception as e:
                    ui.notify(
                        f"保存失败：{str(e)}",
                        position="top",
                        type="negative",
                    )

            with ui.row().classes("w-full gap-4"):
                ui.button(
                    "生成提示词",
                    on_click=build_prompt_from_fields,
                ).classes("bg-slate-600 text-white")
                ui.button(
                    "保存提示词",
                    on_click=save_prompt,
                ).classes("bg-blue-600 text-white")
                ui.button(
                    "AI 生成",
                    on_click=run_ai_task,
                ).classes("bg-purple-600 text-white")
                ui.button(
                    "保存到表单",
                    on_click=save_ai_output_to_storage,
                ).classes("bg-green-600 text-white")


if __name__ in {"__main__", "__mp_main__"}:
    ui.run()
