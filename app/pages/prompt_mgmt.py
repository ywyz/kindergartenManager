"""提示词管理页面 - 查看/编辑/新建/删除提示词，支持测试"""
from nicegui import ui

from app.services.plan_service import (
    PROMPT_CATEGORIES, get_prompts, save_prompt,
    set_prompt_active, delete_prompt,
)


def prompt_mgmt_page():
    ui.page_title("提示词管理 - 幼儿园每日活动计划")

    state = {
        "editing_id": None,
        "editing_category": None,
    }

    with ui.column().classes("w-full max-w-5xl mx-auto p-4 gap-4"):
        ui.label("✍️ 提示词管理").classes("text-2xl font-bold")
        ui.label(
            "提示词支持以下占位符变量：{grade}（年级）、{class_name}（班级）、"
            "{week}（第几周）、{day}（星期几）、{content}（输入内容）、"
            "{area_content}（区域内容）、{outdoor_content}（户外内容）、"
            "{holiday_tip}（节假日提示）"
        ).classes("text-sm text-gray-500 bg-gray-50 p-2 rounded")

        # ---- 分类选择 ----
        category_tabs = ui.tabs().classes("w-full")
        cat_tab_map = {}
        with category_tabs:
            for cat_key, cat_label in PROMPT_CATEGORIES.items():
                tab = ui.tab(cat_label)
                cat_tab_map[cat_key] = tab

        # ---- 编辑区 ----
        with ui.card().classes("w-full"):
            ui.label("新建 / 编辑提示词").classes("text-lg font-semibold")
            edit_name = ui.input("提示词名称", placeholder="例：教案拆分-默认").classes("w-full")
            edit_category = ui.select(
                {k: v for k, v in PROMPT_CATEGORIES.items()},
                label="分类",
                value=list(PROMPT_CATEGORIES.keys())[0],
            ).classes("w-full")
            edit_content = ui.textarea(
                "提示词内容",
                placeholder="请输入提示词内容，使用 {grade}、{content} 等占位符...",
            ).classes("w-full").props("rows=10")

            edit_status = ui.label("").classes("text-sm")

            with ui.row().classes("gap-2"):
                save_btn = ui.button("💾 保存提示词", color="primary")
                clear_btn = ui.button("🗑 清空", color="grey")

            def do_save_prompt():
                name = edit_name.value.strip()
                content = edit_content.value.strip()
                cat = edit_category.value
                if not name or not content:
                    edit_status.set_text("❌ 名称和内容不能为空")
                    return
                prompt_id = save_prompt(name, cat, content, state["editing_id"])
                state["editing_id"] = None
                edit_status.set_text(f"✅ 已保存（ID: {prompt_id}）")
                _refresh_list()

            def do_clear():
                state["editing_id"] = None
                edit_name.set_value("")
                edit_content.set_value("")
                edit_status.set_text("")

            save_btn.on("click", do_save_prompt)
            clear_btn.on("click", do_clear)

        # ---- 提示词测试区 ----
        with ui.card().classes("w-full"):
            ui.label("🧪 测试提示词").classes("text-lg font-semibold")
            test_input = ui.textarea(
                "测试输入内容",
                placeholder="输入测试内容（将替换提示词中的 {content} 占位符）...",
            ).classes("w-full").props("rows=3")

            test_result = ui.textarea(
                "AI 响应结果",
                placeholder="点击测试后 AI 响应将显示在此...",
            ).classes("w-full").props("rows=6 readonly")

            test_status = ui.label("").classes("text-sm text-gray-500")
            test_btn = ui.button("🚀 发送测试", color="orange")

            async def do_test():
                from app.services.ai_service import get_ai_service
                content = edit_content.value.strip()
                if not content:
                    test_status.set_text("❌ 请先填写提示词内容")
                    return
                ai = get_ai_service()
                if not ai:
                    test_status.set_text("❌ 未配置 AI，请先到设置页面配置")
                    return
                test_btn.props("loading")
                test_status.set_text("⏳ 发送中...")
                try:
                    from nicegui import run
                    result = await run.io_bound(
                        ai.test_prompt, content, test_input.value or "测试内容"
                    )
                    test_result.set_value(result)
                    test_status.set_text("✅ 测试完成")
                except Exception as e:
                    test_status.set_text(f"❌ 测试失败：{e}")
                finally:
                    test_btn.props(remove="loading")

            test_btn.on("click", do_test)

        # ---- 提示词列表 ----
        ui.label("提示词列表").classes("text-lg font-semibold mt-2")
        list_container = ui.column().classes("w-full gap-2")

        def _refresh_list():
            list_container.clear()
            prompts = get_prompts()
            if not prompts:
                with list_container:
                    ui.label("暂无提示词，可在上方新建。").classes("text-gray-400")
                return

            current_cat = None
            with list_container:
                for p in prompts:
                    cat_key = p.get("prompt_category", "")
                    cat_label = PROMPT_CATEGORIES.get(cat_key, cat_key)
                    if cat_key != current_cat:
                        ui.label(f"── {cat_label} ──").classes("text-sm font-semibold text-gray-600 mt-2")
                        current_cat = cat_key

                    with ui.card().classes("w-full"):
                        with ui.row().classes("items-center justify-between w-full"):
                            with ui.column().classes("flex-1"):
                                is_active = bool(p.get("is_active"))
                                status_tag = (
                                    ui.badge("激活", color="positive")
                                    if is_active
                                    else ui.badge("未激活", color="grey")
                                )
                                ui.label(p.get("prompt_name", "")).classes("font-medium")
                                ui.label(
                                    (p.get("prompt_content") or "")[:80] + "..."
                                ).classes("text-sm text-gray-400")

                            with ui.row().classes("gap-1"):
                                pid = p["id"]
                                pcat = p["prompt_category"]
                                pcontent = p["prompt_content"]
                                pname = p["prompt_name"]

                                if not is_active:
                                    def make_activate(pid=pid, pcat=pcat):
                                        def activate():
                                            set_prompt_active(pid, pcat)
                                            _refresh_list()
                                        return activate
                                    ui.button(
                                        "激活", on_click=make_activate(), color="positive"
                                    ).props("size=sm flat")

                                def make_edit(pid=pid, pname=pname, pcat=pcat, pcontent=pcontent):
                                    def edit_prompt():
                                        state["editing_id"] = pid
                                        edit_name.set_value(pname)
                                        edit_category.set_value(pcat)
                                        edit_content.set_value(pcontent)
                                        edit_status.set_text(f"正在编辑 ID={pid}")
                                        # 滚动到编辑区
                                    return edit_prompt
                                ui.button(
                                    "编辑", on_click=make_edit(), color="primary"
                                ).props("size=sm flat")

                                def make_delete(pid=pid, pname=pname):
                                    def del_prompt():
                                        with ui.dialog() as dialog, ui.card():
                                            ui.label(f"确认删除提示词「{pname}」？")
                                            with ui.row():
                                                ui.button(
                                                    "确认删除",
                                                    on_click=lambda: [
                                                        delete_prompt(pid),
                                                        _refresh_list(),
                                                        dialog.close(),
                                                    ],
                                                    color="negative",
                                                )
                                                ui.button("取消", on_click=dialog.close)
                                        dialog.open()
                                    return del_prompt
                                ui.button(
                                    "删除", on_click=make_delete(), color="negative"
                                ).props("size=sm flat")

        _refresh_list()
