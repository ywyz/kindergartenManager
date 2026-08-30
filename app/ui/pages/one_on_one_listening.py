"""一对一倾听观察记录页面（路由：/one-on-one-listening）。

功能：
  - 表单输入元数据（观察年月、幼儿姓名、成人数目、年级·学期、幼儿年龄、观察者）
  - 自动选取工作日（按年月，排除法定节假日，可手动改）
  - 五大领域分区：每领域 3 日期 + 上传 3 张绘画 + 「生成本领域」→ 回填
    目标 / 3 图描述 / 二级指标星级（可改）/ 综合评价 / 支持策略（均可编辑）
  - 「保存」持久化整条记录
  - 「导出 Word」：合并（1 档）/ 按领域（5 档 zip）

辅助纯函数（供单测）：
  - infer_age_by_grade / default_year_month / validate_image_count
  - build_export_filename / parse_stage_label / format_stage_label
"""

from __future__ import annotations

import base64
import io
import zipfile
from collections.abc import Coroutine
from contextlib import contextmanager
from datetime import date
from typing import Any

from nicegui import ui

from app.core.audit import log_audit
from app.core.database import AsyncSessionLocal
from app.core.exceptions import AiCallError, AiParseError, AppError, ConfigError
from app.core.logging import get_logger
from app.core.unit_of_work import AsyncSessionUnitOfWork
from app.integration.holiday_client.client import get_legal_holidays_in_year
from app.integration.image_processing import (
    CompressedImage,
    compress_image,
    normalize_to_landscape,
)
from app.integration.image_storage import get_storage_backend
from app.integration.word_export.listening_exporter import (
    export_batch_by_domain,
    export_combined,
    export_split_by_domain,
)
from app.repository.class_repository import get_class_config
from app.repository.export_repository import save_export_record
from app.repository.indicator_repository import list_available_stages, list_indicators
from app.repository.listening_image_repository import (
    delete_images_by_record,
)
from app.repository.listening_repository import (
    delete_domains_by_record,
    delete_indicator_results_by_record,
    delete_record,
    list_records,
)
from app.repository.semester_repository import get_active_semester
from app.service.date_service import pick_three_workdays
from app.service.listening_service import (
    generate_domain_content,
    load_record_detail,
    save_record_with_all,
    to_export_payload,
    update_record_with_all,
)
from app.ui.auth_context import require_bound_ui_session, require_current_ui_session
from app.ui.bound_operation import UiOperationGuard
from app.ui.components.app_shell import get_display_name, render_shell
from app.ui.helpers import validate_image_count

logger = get_logger(__name__)

# 五大领域（页面展示顺序）
_UI_DOMAINS = ["健康", "语言", "社会", "艺术", "科学"]
_MONTHS = list(range(1, 13))


# ─── 纯函数（单测友好）────────────────────────────────────────────────────────


def infer_age_by_grade(grade: str | None) -> str:
    """按年级推断幼儿年龄：小班 4 岁、中班 5 岁、大班 6 岁。"""
    return {"小班": "4岁", "中班": "5岁", "大班": "6岁"}.get((grade or "").strip(), "")


def default_year_month(today: date | None = None) -> tuple[int, int]:
    """返回默认观察年月（当前年月）。"""
    d = today or date.today()
    return d.year, d.month


def format_stage_label(grade: str, term: str) -> str:
    """(grade, term) → 显示标签『小班·下学期』。"""
    return f"{grade}·{term}"


def parse_stage_label(label: str) -> tuple[str, str]:
    """显示标签『小班·下学期』→ (grade, term)。"""
    parts = (label or "").split("·", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return label, ""


def build_export_filename(
    tenant_id: int, user_id: int, child_name: str, year: int, month: int, suffix: str
) -> str:
    """构造导出文件名：{租户}_{用户}_{幼儿}_{年}{月}_一对一倾听_{suffix}.docx。"""
    safe_name = (child_name or "幼儿").strip().replace("/", "_").replace(" ", "")
    return (
        f"{tenant_id}_{user_id}_{safe_name}_{year}年{month}月_一对一倾听_{suffix}.docx"
    )


def build_batch_export_filename(
    tenant_id: int, user_id: int, year: int, month: int, count: int
) -> str:
    """构造批量按领域导出的 zip 文件名。"""
    return (
        f"{tenant_id}_{user_id}_{year}年{month}月_一对一倾听_批量按领域_{count}人.zip"
    )


def validate_bulk_import_count(count: int, minimum: int = 15) -> bool:
    """一键导入校验：至少 15 张（5 领域 × 3 张）；超出的按文件名取前 15。"""
    return count >= minimum


def distribute_images_by_filename(
    files: list[tuple[str, bytes]], domains: list[str], per_domain: int = 3
) -> dict[str, list[bytes]]:
    """按文件名排序后，每 per_domain 张依次分配给 domains 顺序的各领域。

    Args:
        files: [(文件名, 字节), ...]。
        domains: 领域顺序（如 [健康, 语言, 社会, 艺术, 科学]）。
        per_domain: 每领域分配张数。

    Returns:
        {领域: [字节, ...]}。
    """
    ordered = sorted(files, key=lambda f: f[0])
    result: dict[str, list[bytes]] = {}
    for i, domain in enumerate(domains):
        chunk = ordered[i * per_domain : (i + 1) * per_domain]
        result[domain] = [b for _name, b in chunk]
    return result


def pack_domain_files_to_zip(files: dict[str, bytes]) -> bytes:
    """将 {领域: docx 字节} 打包为 zip 字节。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for domain, content in files.items():
            zf.writestr(f"{domain}.docx", content)
    return buf.getvalue()


def format_record_summary(
    child_name: str | None,
    obs_year: int | None,
    obs_month: int | None,
    grade: str | None,
    term: str | None,
    observer: str | None,
) -> str:
    """历史列表条目摘要文本。"""
    stage = format_stage_label(grade or "", term or "").strip("·")
    parts = [
        f"{obs_year or '-'}年{obs_month or '-'}月",
        child_name or "未命名",
        stage,
        observer or "",
    ]
    return "  ".join(p for p in parts if p)


def _parse_iso_date(value: str | None) -> date | None:
    """容错解析 YYYY-MM-DD，失败返回 None。"""
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        return None


async def _auto_pick_workdays(year: int, month: int) -> tuple[list[date], bool]:
    """单次查询整年法定节假日（避免逐日并发触发限流），随机返回本月 3 个工作日。

    Returns:
        (dates, holidays_available)：holidays_available=False 表示节假日接口不可用（已降级，需人工核对）。
    """
    holidays = await get_legal_holidays_in_year(year)
    holiday_set = holidays or set()
    dates = pick_three_workdays(year, month, is_holiday=lambda d: d in holiday_set)
    return dates, holidays is not None


# ─── 页面路由 ──────────────────────────────────────────────────────────────────


@ui.page("/one-on-one-listening")
async def one_on_one_listening_page() -> None:
    ui_session = await require_current_ui_session()
    if ui_session is None:
        return
    tenant_id = ui_session.tenant_id
    user_id = ui_session.user_id

    async def _require_bound_session() -> bool:
        return await require_bound_ui_session(ui_session) is not None

    # 取班级 / 学期默认值
    grade_default = ""
    class_name_default = ""
    term_default = ""
    async with AsyncSessionLocal() as session:
        cls_cfg = await get_class_config(session, tenant_id, user_id)
        if cls_cfg:
            grade_default = cls_cfg.grade or ""
            class_name_default = cls_cfg.class_name or ""
        sem = await get_active_semester(session, tenant_id, user_id)
        if sem and sem.semester_name:
            if "下" in sem.semester_name:
                term_default = "下学期"
            elif "上" in sem.semester_name:
                term_default = "上学期"
        stages = await list_available_stages(session, tenant_id)

    if not await _require_bound_session():
        return

    # 学段下拉选项
    stage_labels = [format_stage_label(g, t) for g, t in stages] or ["小班·下学期"]
    default_stage = format_stage_label(
        grade_default or "小班", term_default or "下学期"
    )
    if default_stage not in stage_labels:
        default_stage = stage_labels[0]

    shell_user = ui_session.as_user_dict()
    await render_shell(shell_user, active="one-on-one-listening")
    if not await _require_bound_session():
        return

    observer_default = get_display_name(shell_user)
    cur_year, cur_month = default_year_month()

    # 每领域状态：raw_images / compressed / 各 widget 引用 / 指标行
    domain_states: dict[str, dict] = {}
    # 一键导入暂存：list[(文件名, 字节)]
    bulk_state: dict = {"files": []}
    # 编辑状态：record_id 非空表示覆盖更新已有记录
    edit_state: dict = {"record_id": None}
    # 表单与历史区分别使用单调代次；只存在于当前页面生命周期。
    form_generation = [0]
    history_generation = [0]
    bulk_generation = [0]
    suppress_form_events = [0]
    action_guard = UiOperationGuard()

    def _form_is_current(generation: int) -> bool:
        return generation == form_generation[0]

    def _history_is_current(generation: int) -> bool:
        return generation == history_generation[0]

    def _advance_form_generation() -> int:
        form_generation[0] += 1
        return form_generation[0]

    def _advance_history_generation() -> int:
        history_generation[0] += 1
        return history_generation[0]

    def _invalidate_form(*_event_args: object) -> None:
        if not suppress_form_events[0]:
            _advance_form_generation()

    def _invalidate_history(*_event_args: object) -> None:
        _advance_history_generation()

    @contextmanager
    def _programmatic_form_update():
        suppress_form_events[0] += 1
        try:
            yield
        finally:
            suppress_form_events[0] -= 1

    async def _run_claimed_action(
        slot: str,
        owner: object,
        operation: Coroutine[Any, Any, None],
    ) -> None:
        try:
            await operation
        finally:
            action_guard.release(slot, owner)

    with ui.column().classes("w-full max-w-5xl mx-auto p-6 gap-4"):
        ui.label("一对一倾听观察记录").classes("text-2xl font-bold text-indigo-700")
        if grade_default or class_name_default:
            ui.label(f"班级：{grade_default} {class_name_default}").classes(
                "text-gray-500 text-sm"
            )

        error_label = ui.label("").classes("text-red-600 text-sm hidden")
        status_label = ui.label("").classes("text-blue-600 text-sm hidden")

        def show_error(msg: str) -> None:
            error_label.set_text(msg)
            error_label.classes(remove="hidden")
            status_label.classes(add="hidden")

        def show_info(msg: str, ok: bool = False) -> None:
            status_label.set_text(msg)
            status_label.classes(remove="hidden text-blue-600 text-green-600")
            status_label.classes(add="text-green-600" if ok else "text-blue-600")
            error_label.classes(add="hidden")

        # ── 基本信息 ──────────────────────────────────────────────
        with ui.card().classes("w-full"):
            ui.label("基本信息").classes("font-semibold text-gray-700 mb-2")
            with ui.row().classes("w-full gap-4 flex-wrap items-end"):
                year_input = ui.number(
                    label="观察年", value=cur_year, min=2020, max=2100, format="%d"
                ).classes("w-28")
                month_select = ui.select(
                    label="观察月", options=_MONTHS, value=cur_month
                ).classes("w-24")
                child_name_input = ui.input(
                    label="幼儿姓名", placeholder="单个幼儿"
                ).classes("flex-1 min-w-40")
                adult_count_input = ui.number(label="成人数目", value=1, min=1).classes(
                    "w-28"
                )

            with ui.row().classes("w-full gap-4 flex-wrap items-end"):
                stage_select = ui.select(
                    label="年级·学期（指标版本）",
                    options=stage_labels,
                    value=default_stage,
                ).classes("w-52")
                child_age_input = ui.input(
                    label="幼儿年龄",
                    value=infer_age_by_grade(grade_default or "小班"),
                ).classes("w-28")
                observer_input = ui.input(
                    label="观察者", value=observer_default
                ).classes("flex-1 min-w-40")

            with ui.row().classes("w-full gap-3 items-center flex-wrap"):
                autopick_btn = ui.button(
                    "一键为所有领域按各自年月选取工作日", icon="event_available"
                ).props("outline")
                ui.label(
                    "各领域按其自身年月，从前三周各取一个工作日（排除法定节假日）"
                ).classes("text-xs text-gray-400")

            ui.separator().classes("my-1")
            ui.label(
                "一键导入照片（恰好 15 张，按文件名排序自动分配五领域，每领域 3 张，统一横版）"
            ).classes("text-sm text-gray-600")
            with ui.row().classes("w-full gap-3 items-center flex-wrap"):
                bulk_count_label = ui.label("已选 0 张").classes(
                    "text-gray-500 text-sm"
                )
                apply_bulk_btn = ui.button("分配到五领域", icon="auto_fix_high").props(
                    "outline"
                )
                generate_all_btn = ui.button(
                    "生成全部领域", icon="auto_awesome"
                ).classes("bg-indigo-600 text-white")
            ui.upload(
                on_upload=lambda e: trigger_bulk_upload(e),
                auto_upload=True,
                multiple=True,
            ).props("accept=image/*").classes("w-full")

        # ── 编辑状态横幅 ──────────────────────────────────────────
        with ui.row().classes("w-full gap-3 items-center"):
            edit_banner = ui.label("").classes(
                "text-amber-700 text-sm font-semibold hidden"
            )
            cancel_edit_btn = (
                ui.button("取消编辑 / 新建", icon="close")
                .props("flat dense")
                .classes("hidden")
            )

        domains_container = ui.column().classes("w-full gap-3")

        # ── 操作按钮 ──────────────────────────────────────────────
        with ui.row().classes("w-full gap-3 justify-end mt-2"):
            save_btn = ui.button("保存", icon="save").classes("bg-blue-600 text-white")
            export_combined_btn = ui.button("导出合并 Word", icon="download").classes(
                "bg-orange-500 text-white"
            )
            export_split_btn = ui.button("导出按领域(zip)", icon="folder_zip").props(
                "outline"
            )

    for control in (
        year_input,
        month_select,
        child_name_input,
        adult_count_input,
        child_age_input,
        observer_input,
    ):
        control.on("update:model-value", _invalidate_form)

    # ── 领域分区渲染 ───────────────────────────────────────────────
    def _on_grade_age_sync() -> None:
        g, _t = parse_stage_label(stage_select.value or default_stage)
        with _programmatic_form_update():
            child_age_input.value = infer_age_by_grade(g)

    async def render_domains(generation: int, stage_label: str) -> None:
        if not await _require_bound_session():
            return
        if not _form_is_current(generation):
            return
        grade, term = parse_stage_label(stage_label or default_stage)
        async with AsyncSessionLocal() as session:
            catalog_by_domain = {}
            for domain in _UI_DOMAINS:
                catalog_by_domain[domain] = await list_indicators(
                    session,
                    tenant_id,
                    grade,
                    term,
                    domain,
                )
        if not await _require_bound_session() or not _form_is_current(generation):
            return
        domains_container.clear()
        domain_states.clear()
        with domains_container:
            with ui.tabs().classes("w-full") as domain_tabs:
                tab_refs = {d: ui.tab(d) for d in _UI_DOMAINS}
            with ui.tab_panels(domain_tabs, value=tab_refs[_UI_DOMAINS[0]]).classes(
                "w-full"
            ):
                for domain in _UI_DOMAINS:
                    with ui.tab_panel(tab_refs[domain]):
                        _build_domain_section(domain, catalog_by_domain.get(domain, []))

    def trigger_render_domains(*_event_args: object):
        _on_grade_age_sync()
        _advance_form_generation()
        generation = form_generation[0]
        stage_label = str(stage_select.value or default_stage)
        return render_domains(generation, stage_label)

    def _build_domain_section(domain: str, catalog: list) -> None:
        st: dict = {
            "raw_images": [],
            "compressed": None,
            "desc_areas": [],
            "date_inputs": [],
            "indicators": [],
        }
        domain_states[domain] = st

        async def _on_upload(e, d: str, s: dict) -> None:
            if not await _require_bound_session():
                return
            if domain_states.get(d) is not s:
                return
            if len(s["raw_images"]) >= 3:
                show_error(f"{d}领域最多 3 张图片")
                return
            raw = await e.file.read() if hasattr(e, "file") else e.content.read()
            if not await _require_bound_session() or domain_states.get(d) is not s:
                return
            try:
                data = normalize_to_landscape(raw)
            except AppError as ex:
                show_error(f"{d}领域图片处理失败：{ex.message}")
                return
            if len(s["raw_images"]) >= 3:
                show_error(f"{d}领域最多 3 张图片")
                return
            s["raw_images"].append(data)
            s["compressed"] = None
            _advance_form_generation()
            s["count_label"].set_text(f"已上传：{len(s['raw_images'])} 张")
            with s["preview_row"]:
                ui.image(
                    f"data:image/jpeg;base64,{base64.b64encode(data).decode()}"
                ).classes("w-20 h-20 object-cover rounded border")

        def trigger_upload(e, d=domain, s=st):
            if domain_states.get(d) is not s:
                return None
            return _on_upload(e, d, s)

        with ui.column().classes("w-full p-1 gap-3"):
            with ui.row().classes("w-full gap-3 flex-wrap items-end"):
                st["year"] = ui.number(
                    label="年",
                    value=int(year_input.value or cur_year),
                    min=2020,
                    max=2100,
                    format="%d",
                ).classes("w-24")
                st["month"] = ui.select(
                    label="月",
                    options=_MONTHS,
                    value=int(month_select.value or cur_month),
                ).classes("w-20")
                for i in range(3):
                    st["date_inputs"].append(
                        ui.input(
                            label=f"日期{i + 1}",
                            placeholder="YYYY-MM-DD",
                        ).classes("w-36")
                    )
                pick_btn = ui.button(
                    "自动选取本领域工作日",
                    icon="event_available",
                ).props("outline dense")
                st["pick_btn"] = pick_btn

            with ui.row().classes("w-full gap-4 items-center"):
                st["count_label"] = ui.label("已上传：0 张").classes(
                    "text-gray-500 text-sm"
                )
                st["preview_row"] = ui.row().classes("gap-2 flex-wrap")

            ui.upload(
                on_upload=trigger_upload,
                auto_upload=True,
                multiple=True,
            ).props("accept=image/*").classes("w-full")

            gen_btn = ui.button(
                f"生成{domain}领域",
                icon="auto_awesome",
            ).classes("bg-indigo-600 text-white")
            st["gen_btn"] = gen_btn
            st["goals"] = ui.textarea(label="目标（1~2 点）").classes("w-full")
            with ui.column().classes("w-full gap-1"):
                ui.label("图片描述（一对一倾听记录）").classes("text-sm text-gray-600")
                for i in range(3):
                    st["desc_areas"].append(
                        ui.textarea(label=f"图{i + 1}描述").classes("w-full")
                    )

            with ui.expansion(
                f"二级指标评定（{len(catalog)} 项）",
                icon="star",
            ).classes("w-full"):
                if not catalog:
                    ui.label("未找到该领域指标，请检查年级·学期配置").classes(
                        "text-amber-600 text-sm"
                    )
                for cat in catalog:
                    with ui.row().classes("w-full items-center gap-2 border-b py-1"):
                        ui.label(f"[{cat.sort_order}] {cat.level2_name}").classes(
                            "flex-1 text-xs text-gray-700"
                        )
                        select = ui.select(
                            options={1: "★", 2: "★★", 3: "★★★"},
                            value=3,
                        ).classes("w-24")
                        st["indicators"].append(
                            {
                                "catalog_id": cat.id,
                                "sort_order": cat.sort_order,
                                "select": select,
                            }
                        )

            st["eval"] = ui.textarea(label="综合评价（约 200 字）").classes("w-full")
            st["strategy"] = ui.textarea(label="支持策略（约 200 字）").classes(
                "w-full"
            )

        for control in (
            st["year"],
            st["month"],
            *st["date_inputs"],
            st["goals"],
            *st["desc_areas"],
            *(item["select"] for item in st["indicators"]),
            st["eval"],
            st["strategy"],
        ):
            control.on("update:model-value", _invalidate_form)

        async def _do_generate(
            generation: int,
            images: tuple[bytes, ...],
            context: dict[str, str],
            owner: object,
            d: str,
            s: dict,
        ) -> int | None:
            if not await _require_bound_session():
                return None
            if not _form_is_current(generation) or domain_states.get(d) is not s:
                return None
            s["gen_btn"].props("loading=true")
            try:
                if not validate_image_count(len(images)):
                    show_error(f"{d}领域请先上传 1~3 张绘画照片")
                    return None
                show_info(f"⏳ 正在生成{d}领域……")
                async with AsyncSessionLocal() as session:
                    result = await generate_domain_content(
                        session=session,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        domain=d,
                        images=list(images),
                        context=dict(context),
                    )
                if (
                    not await _require_bound_session()
                    or not _form_is_current(generation)
                    or domain_states.get(d) is not s
                ):
                    return None
                with _programmatic_form_update():
                    s["compressed"] = result["compressed_images"]
                    s["goals"].value = result["goals"]
                    descriptions = result["image_descriptions"]
                    for i, area in enumerate(s["desc_areas"]):
                        area.value = descriptions[i] if i < len(descriptions) else ""
                    stars_by_order = {
                        item["sort_order"]: item["stars"]
                        for item in result["indicator_results"]
                    }
                    for indicator in s["indicators"]:
                        indicator["select"].value = stars_by_order.get(
                            indicator["sort_order"],
                            3,
                        )
                    s["eval"].value = result["evaluation"]
                    s["strategy"].value = result["support_strategy"]
                generation = _advance_form_generation()
                show_info(f"{d}领域生成成功，请检查后保存", ok=True)
                return generation
            except ConfigError:
                if (
                    not await _require_bound_session()
                    or not _form_is_current(generation)
                    or domain_states.get(d) is not s
                ):
                    return None
                show_error("AI 配置不可用，请检查模型配置")
            except (AiCallError, AiParseError):
                if (
                    not await _require_bound_session()
                    or not _form_is_current(generation)
                    or domain_states.get(d) is not s
                ):
                    return None
                show_error("AI 调用或解析失败，请稍后重试")
            except AppError as ex:
                if (
                    not await _require_bound_session()
                    or not _form_is_current(generation)
                    or domain_states.get(d) is not s
                ):
                    return None
                show_error(f"生成失败：{ex.message}")
            except Exception as ex:  # noqa: BLE001
                if (
                    not await _require_bound_session()
                    or not _form_is_current(generation)
                    or domain_states.get(d) is not s
                ):
                    return None
                logger.error("生成倾听领域失败 error_type=%s", type(ex).__name__)
                show_error(f"生成失败：{type(ex).__name__}")
            finally:
                if (
                    action_guard.owns("listening.generate", owner)
                    and await _require_bound_session()
                ):
                    s["gen_btn"].props(remove="loading")
            return None

        def trigger_generate(*_event_args: object, d=domain, s=st):
            generation = form_generation[0]
            images = tuple(s["raw_images"])
            grade, term = parse_stage_label(stage_select.value or default_stage)
            context = {
                "grade": grade,
                "term": term,
                "child_name": str(child_name_input.value or ""),
                "child_age": str(child_age_input.value or ""),
            }
            owner = action_guard.claim("listening.generate")
            if owner is None:
                return None
            return _run_claimed_action(
                "listening.generate",
                owner,
                _do_generate(generation, images, context, owner, d, s),
            )

        async def _pick_domain_workdays(
            generation: int,
            year: int,
            month: int,
            owner: object,
            d: str,
            s: dict,
        ) -> None:
            if not await _require_bound_session():
                return
            if not _form_is_current(generation) or domain_states.get(d) is not s:
                return
            s["pick_btn"].props("loading=true")
            try:
                workdays, holidays_available = await _auto_pick_workdays(year, month)
                if (
                    not await _require_bound_session()
                    or not _form_is_current(generation)
                    or domain_states.get(d) is not s
                ):
                    return
                with _programmatic_form_update():
                    for i, date_input in enumerate(s["date_inputs"]):
                        date_input.value = (
                            workdays[i].isoformat() if i < len(workdays) else ""
                        )
                generation = _advance_form_generation()
                note = (
                    "" if holidays_available else "（节假日信息暂不可用，请人工核对）"
                )
                if len(workdays) < 3:
                    show_info(
                        f"{d}领域仅找到 {len(workdays)} 个工作日，请手动补全{note}"
                    )
                else:
                    show_info(
                        f"{d}领域工作日已填入，可手动调整{note}",
                        ok=holidays_available,
                    )
            except Exception as ex:  # noqa: BLE001
                if (
                    not await _require_bound_session()
                    or not _form_is_current(generation)
                    or domain_states.get(d) is not s
                ):
                    return
                logger.error("领域自动选取工作日失败 error_type=%s", type(ex).__name__)
                show_error(f"自动选取失败：{type(ex).__name__}")
            finally:
                if (
                    action_guard.owns("listening.workdays", owner)
                    and await _require_bound_session()
                ):
                    s["pick_btn"].props(remove="loading")

        def trigger_pick_workdays(*_event_args: object, d=domain, s=st):
            generation = form_generation[0]
            year = int(s["year"].value or year_input.value or cur_year)
            month = int(s["month"].value or month_select.value or cur_month)
            owner = action_guard.claim("listening.workdays")
            if owner is None:
                return None
            return _run_claimed_action(
                "listening.workdays",
                owner,
                _pick_domain_workdays(generation, year, month, owner, d, s),
            )

        st["do_generate"] = _do_generate
        pick_btn.on("click", trigger_pick_workdays)
        gen_btn.on("click", trigger_generate)

    # ── 自动选取工作日（各领域按自身年月）────────────────────────────
    async def do_autopick_all(
        generation: int,
        targets: tuple[tuple[str, dict, int, int], ...],
        owner: object,
    ) -> None:
        if not await _require_bound_session():
            return
        if not _form_is_current(generation):
            return
        autopick_btn.props("loading=true")
        try:
            any_short = False
            any_hol_unavailable = False
            results: list[tuple[str, dict, list[date], bool]] = []
            for domain, state, year, month in targets:
                if domain_states.get(domain) is not state:
                    return
                workdays, holidays_available = await _auto_pick_workdays(year, month)
                if (
                    not await _require_bound_session()
                    or not _form_is_current(generation)
                    or domain_states.get(domain) is not state
                ):
                    return
                results.append((domain, state, workdays, holidays_available))
                if not holidays_available:
                    any_hol_unavailable = True
                if len(workdays) < 3:
                    any_short = True
            with _programmatic_form_update():
                for _domain, state, workdays, _holidays_available in results:
                    for i, date_input in enumerate(state["date_inputs"]):
                        date_input.value = (
                            workdays[i].isoformat() if i < len(workdays) else ""
                        )
            generation = _advance_form_generation()
            note = "（节假日信息暂不可用，请人工核对）" if any_hol_unavailable else ""
            if any_short:
                show_info(
                    f"已按各领域年月填入工作日；部分领域不足 3 天，请手动补全{note}"
                )
            else:
                show_info(
                    f"已按各领域年月填入工作日，可手动调整{note}",
                    ok=not any_hol_unavailable,
                )
        except Exception as ex:  # noqa: BLE001
            if not await _require_bound_session() or not _form_is_current(generation):
                return
            logger.error("自动选取工作日失败 error_type=%s", type(ex).__name__)
            show_error(f"自动选取失败：{type(ex).__name__}")
        finally:
            if (
                action_guard.owns("listening.workdays", owner)
                and await _require_bound_session()
            ):
                autopick_btn.props(remove="loading")

    def trigger_autopick_all(*_event_args: object):
        generation = form_generation[0]
        targets = [
            (
                domain,
                state,
                int(state["year"].value or year_input.value or cur_year),
                int(state["month"].value or month_select.value or cur_month),
            )
            for domain, state in domain_states.items()
        ]
        frozen_targets = tuple(targets)
        owner = action_guard.claim("listening.workdays")
        if owner is None:
            return None
        return _run_claimed_action(
            "listening.workdays",
            owner,
            do_autopick_all(generation, frozen_targets, owner),
        )

    # ── 一键导入照片 ───────────────────────────────────────────────
    async def _on_bulk_upload(e, generation: int, name: str) -> None:
        if not await _require_bound_session():
            return
        if generation != bulk_generation[0]:
            return
        raw = await e.file.read() if hasattr(e, "file") else e.content.read()
        if not await _require_bound_session() or generation != bulk_generation[0]:
            return
        bulk_state["files"].append((name, raw))
        bulk_count_label.set_text(f"已选 {len(bulk_state['files'])} 张")

    def trigger_bulk_upload(e):
        generation = bulk_generation[0]
        name = str(getattr(e, "name", "") or f"img{len(bulk_state['files']):02d}")
        return _on_bulk_upload(e, generation, name)

    def _render_domain_previews(st: dict) -> None:
        st["preview_row"].clear()
        st["count_label"].set_text(f"已上传：{len(st['raw_images'])} 张")
        with st["preview_row"]:
            for b in st["raw_images"]:
                ui.image(
                    f"data:image/jpeg;base64,{base64.b64encode(b).decode()}"
                ).classes("w-20 h-20 object-cover rounded border")

    async def do_apply_bulk(
        generation: int,
        bulk_epoch: int,
        files: tuple[tuple[str, bytes], ...],
        targets: tuple[tuple[str, dict], ...],
    ) -> None:
        if not await _require_bound_session():
            return
        if (
            not _form_is_current(generation)
            or bulk_epoch != bulk_generation[0]
            or any(domain_states.get(domain) is not state for domain, state in targets)
        ):
            return
        if not validate_bulk_import_count(len(files)):
            show_error(f"一键导入至少需要 15 张照片（当前 {len(files)} 张）")
            return
        try:
            total = len(files)
            distributed = distribute_images_by_filename(
                list(files),
                _UI_DOMAINS,
                per_domain=3,
            )
            normalized = {
                domain: [normalize_to_landscape(data) for data in images]
                for domain, images in distributed.items()
            }
            with _programmatic_form_update():
                for domain, state in targets:
                    state["raw_images"] = normalized.get(domain, [])
                    state["compressed"] = None
                    _render_domain_previews(state)
            bulk_state["files"] = []
            bulk_generation[0] += 1
            generation = _advance_form_generation()
            bulk_count_label.set_text("已选 0 张")
            extra = f"（共上传 {total} 张，已按文件名取前 15 张）" if total > 15 else ""
            show_info(
                f"已分配到五领域（每领域 3 张，统一横版）{extra}，请逐领域或一键生成",
                ok=True,
            )
        except AppError as ex:
            show_error(f"图片处理失败：{ex.message}")
        except Exception as ex:  # noqa: BLE001
            logger.error("一键导入分配失败 error_type=%s", type(ex).__name__)
            show_error(f"导入失败：{type(ex).__name__}")

    def trigger_apply_bulk(*_event_args: object):
        generation = form_generation[0]
        bulk_epoch = bulk_generation[0]
        files = tuple(bulk_state["files"])
        targets = tuple((domain, state) for domain, state in domain_states.items())
        return do_apply_bulk(generation, bulk_epoch, files, targets)

    async def do_generate_all(
        generation: int,
        targets: tuple[tuple[str, dict, tuple[bytes, ...], dict[str, str]], ...],
        owner: object,
    ) -> None:
        if not await _require_bound_session():
            return
        if not _form_is_current(generation):
            return
        generate_all_btn.props("loading=true")
        try:
            if not targets:
                show_error("请先上传/导入照片再生成")
                return
            for domain, state, images, context in targets:
                next_generation = await state["do_generate"](
                    generation,
                    images,
                    context,
                    owner,
                    domain,
                    state,
                )
                if next_generation is None:
                    return
                generation = next_generation
            if not await _require_bound_session() or not _form_is_current(generation):
                return
            show_info("全部领域生成完成，请检查后保存", ok=True)
        finally:
            if (
                action_guard.owns("listening.generate", owner)
                and await _require_bound_session()
            ):
                generate_all_btn.props(remove="loading")

    def trigger_generate_all(*_event_args: object):
        generation = form_generation[0]
        grade, term = parse_stage_label(stage_select.value or default_stage)
        targets = []
        for domain in _UI_DOMAINS:
            state = domain_states.get(domain)
            if not state or not state["raw_images"]:
                continue
            context = {
                "grade": grade,
                "term": term,
                "child_name": str(child_name_input.value or ""),
                "child_age": str(child_age_input.value or ""),
            }
            targets.append((domain, state, tuple(state["raw_images"]), context))
        frozen_targets = tuple(targets)
        owner = action_guard.claim("listening.generate")
        if owner is None:
            return None
        return _run_claimed_action(
            "listening.generate",
            owner,
            do_generate_all(generation, frozen_targets, owner),
        )

    autopick_btn.on("click", trigger_autopick_all)
    apply_bulk_btn.on("click", trigger_apply_bulk)
    generate_all_btn.on("click", trigger_generate_all)
    stage_select.on("update:model-value", trigger_render_domains)

    def _build_domain_payload(domain: str) -> dict | None:
        """从领域 widget 状态构建完整 payload（保存 + 导出共用）。返回 None 表示该领域无内容。"""
        st = domain_states.get(domain)
        if not st:
            return None
        compressed = st.get("compressed")
        if compressed is None and st["raw_images"]:
            compressed = [compress_image(b) for b in st["raw_images"]]
        compressed = compressed or []
        descriptions = [a.value or "" for a in st["desc_areas"]][: len(compressed)]
        # 无图片且无文本则视为空领域
        has_content = bool(compressed) or bool((st["goals"].value or "").strip())
        if not has_content:
            return None
        indicator_results = [
            {
                "catalog_id": ind["catalog_id"],
                "sort_order": ind["sort_order"],
                "stars": int(ind["select"].value or 3),
            }
            for ind in st["indicators"]
        ]
        images = [
            (compressed[i].data, descriptions[i] if i < len(descriptions) else "")
            for i in range(len(compressed))
        ]
        return {
            "domain": domain,
            "obs_year": int(st["year"].value or year_input.value or cur_year),
            "obs_month": int(st["month"].value or month_select.value or cur_month),
            "date_1": _parse_iso_date(st["date_inputs"][0].value),
            "date_2": _parse_iso_date(st["date_inputs"][1].value),
            "date_3": _parse_iso_date(st["date_inputs"][2].value),
            "goals": st["goals"].value or None,
            "evaluation": st["eval"].value or None,
            "support_strategy": st["strategy"].value or None,
            "compressed_images": compressed,
            "image_descriptions": descriptions,
            "indicator_results": indicator_results,
            "images": images,
            "indicators": indicator_results,
        }

    def _collect() -> tuple[dict, list[dict]]:
        grade, term = parse_stage_label(stage_select.value or default_stage)
        record = {
            "child_name": (child_name_input.value or "").strip(),
            "adult_count": int(adult_count_input.value or 1),
            "child_age": child_age_input.value or None,
        }
        record_full = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "obs_year": int(year_input.value or cur_year),
            "obs_month": int(month_select.value or cur_month),
            "grade": grade or None,
            "term": term or None,
            "class_name": class_name_default or None,
            "observer": observer_input.value or None,
            **record,
        }
        domains = [p for d in _UI_DOMAINS if (p := _build_domain_payload(d))]
        return record_full, domains

    async def do_save(
        generation: int,
        record_full: dict,
        domains: tuple[dict, ...],
        record_id: int | None,
        owner: object,
    ) -> None:
        if not await _require_bound_session():
            return
        if not _form_is_current(generation):
            return
        save_btn.props("loading=true")
        try:
            if not record_full["child_name"]:
                show_error("请填写幼儿姓名")
                return
            if not domains:
                show_error("请至少为一个领域上传图片并生成内容")
                return
            is_edit = record_id is not None
            async with AsyncSessionLocal() as session:
                if is_edit:
                    rid = await update_record_with_all(
                        session,
                        record_id=record_id,
                        record_data=record_full,
                        domains=list(domains),
                        storage=get_storage_backend(),
                    )
                else:
                    rid = await save_record_with_all(
                        session,
                        record_data=record_full,
                        domains=list(domains),
                        storage=get_storage_backend(),
                    )
            if not await _require_bound_session() or not _form_is_current(generation):
                return
            action = "覆盖保存" if is_edit else "保存"
            show_info(f"{action}成功（记录 ID：{rid}）", ok=True)
            refresh_operation = trigger_refresh_history()
            if refresh_operation is not None:
                await refresh_operation
        except Exception as ex:  # noqa: BLE001
            if not await _require_bound_session() or not _form_is_current(generation):
                return
            logger.error("保存倾听记录失败 error_type=%s", type(ex).__name__)
            show_error(f"保存失败：{type(ex).__name__}")
        finally:
            if (
                action_guard.owns("listening.save", owner)
                and await _require_bound_session()
            ):
                save_btn.props(remove="loading")

    def trigger_save(*_event_args: object):
        generation = form_generation[0]
        record_full, domains = _collect()
        record_id = edit_state.get("record_id")
        owner = action_guard.claim("listening.save")
        if owner is None:
            return None
        return _run_claimed_action(
            "listening.save",
            owner,
            do_save(generation, record_full, tuple(domains), record_id, owner),
        )

    save_btn.on("click", trigger_save)

    def _export_record_dict() -> dict:
        return {
            "child_name": (child_name_input.value or "").strip(),
            "adult_count": int(adult_count_input.value or 1),
            "child_age": child_age_input.value or None,
        }

    async def do_export_combined(
        generation: int,
        record: dict,
        domains: tuple[dict, ...],
        child_name: str,
        year: int,
        month: int,
        record_id: int | None,
        owner: object,
    ) -> None:
        if not await _require_bound_session():
            return
        if not _form_is_current(generation):
            return
        export_combined_btn.props("loading=true")
        try:
            if not domains:
                show_error("没有可导出的领域内容，请先生成")
                return
            data = export_combined(record, list(domains))
            fname = build_export_filename(
                tenant_id,
                user_id,
                child_name or "幼儿",
                year,
                month,
                "合并",
            )
            async with AsyncSessionLocal() as session:
                await save_export_record(
                    session,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    daily_plan_id=None,
                    file_name=fname,
                    file_path=f"exports/{fname}",
                    listening_record_id=record_id,
                )
                await session.commit()
            if not await _require_bound_session() or not _form_is_current(generation):
                return
            log_audit(
                "export_listening",
                tenant_id=tenant_id,
                user_id=user_id,
                file_name=fname,
                listening_record_id=record_id,
                mode="combined",
            )
            ui.download(data, fname)
            show_info(f"导出成功：{fname}", ok=True)
        except Exception as ex:  # noqa: BLE001
            if not await _require_bound_session() or not _form_is_current(generation):
                return
            logger.error("导出合并失败 error_type=%s", type(ex).__name__)
            show_error(f"导出失败：{type(ex).__name__}")
        finally:
            if (
                action_guard.owns("listening.export", owner)
                and await _require_bound_session()
            ):
                export_combined_btn.props(remove="loading")

    async def do_export_split(
        generation: int,
        record: dict,
        domains: tuple[dict, ...],
        child_name: str,
        year: int,
        month: int,
        record_id: int | None,
        owner: object,
    ) -> None:
        if not await _require_bound_session():
            return
        if not _form_is_current(generation):
            return
        export_split_btn.props("loading=true")
        try:
            if not domains:
                show_error("没有可导出的领域内容，请先生成")
                return
            files = export_split_by_domain(record, list(domains))
            zip_bytes = pack_domain_files_to_zip(files)
            zip_name = build_export_filename(
                tenant_id,
                user_id,
                child_name or "幼儿",
                year,
                month,
                "按领域",
            ).replace(".docx", ".zip")
            async with AsyncSessionLocal() as session:
                await save_export_record(
                    session,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    daily_plan_id=None,
                    file_name=zip_name,
                    file_path=f"exports/{zip_name}",
                    listening_record_id=record_id,
                )
                await session.commit()
            if not await _require_bound_session() or not _form_is_current(generation):
                return
            log_audit(
                "export_listening",
                tenant_id=tenant_id,
                user_id=user_id,
                file_name=zip_name,
                listening_record_id=record_id,
                mode="split",
            )
            ui.download(zip_bytes, zip_name)
            show_info(f"导出成功：{zip_name}", ok=True)
        except Exception as ex:  # noqa: BLE001
            if not await _require_bound_session() or not _form_is_current(generation):
                return
            logger.error("导出按领域失败 error_type=%s", type(ex).__name__)
            show_error(f"导出失败：{type(ex).__name__}")
        finally:
            if (
                action_guard.owns("listening.export", owner)
                and await _require_bound_session()
            ):
                export_split_btn.props(remove="loading")

    def trigger_export_combined(*_event_args: object):
        generation = form_generation[0]
        _record_full, domains = _collect()
        record = _export_record_dict()
        child_name = str(child_name_input.value or "幼儿")
        year = int(year_input.value or cur_year)
        month = int(month_select.value or cur_month)
        record_id = edit_state.get("record_id")
        owner = action_guard.claim("listening.export")
        if owner is None:
            return None
        return _run_claimed_action(
            "listening.export",
            owner,
            do_export_combined(
                generation,
                record,
                tuple(domains),
                child_name,
                year,
                month,
                record_id,
                owner,
            ),
        )

    def trigger_export_split(*_event_args: object):
        generation = form_generation[0]
        _record_full, domains = _collect()
        record = _export_record_dict()
        child_name = str(child_name_input.value or "幼儿")
        year = int(year_input.value or cur_year)
        month = int(month_select.value or cur_month)
        record_id = edit_state.get("record_id")
        owner = action_guard.claim("listening.export")
        if owner is None:
            return None
        return _run_claimed_action(
            "listening.export",
            owner,
            do_export_split(
                generation,
                record,
                tuple(domains),
                child_name,
                year,
                month,
                record_id,
                owner,
            ),
        )

    export_combined_btn.on("click", trigger_export_combined)
    export_split_btn.on("click", trigger_export_split)

    # ── 载入编辑 / 取消编辑 ─────────────────────────────────────────
    def _rebuild_compressed(im: dict) -> CompressedImage:
        width = im.get("width") or 0
        height = im.get("height") or 0
        if not width or not height:
            try:
                from PIL import Image

                with Image.open(io.BytesIO(im["data"])) as pim:
                    width, height = pim.size
            except Exception:  # noqa: BLE001
                width, height = 0, 0
        return CompressedImage(
            data=im["data"],
            mime_type=im.get("mime_type") or "image/jpeg",
            width=width,
            height=height,
        )

    async def do_load_for_edit(generation: int, rid: int) -> None:
        if not await _require_bound_session():
            return
        if not _form_is_current(generation):
            return
        async with AsyncSessionLocal() as session:
            detail = await load_record_detail(session, tenant_id, user_id, rid)
        if not await _require_bound_session() or not _form_is_current(generation):
            return
        if not detail:
            show_error("记录不存在")
            return
        rec = detail["record"]
        stage_label = format_stage_label(
            rec["grade"] or "小班", rec["term"] or "下学期"
        )
        await render_domains(generation, stage_label)
        if not await _require_bound_session() or not _form_is_current(generation):
            return
        detail_by_domain = {d["domain"]: d for d in detail["domains"]}
        with _programmatic_form_update():
            year_input.value = rec["obs_year"]
            month_select.value = rec["obs_month"]
            child_name_input.value = rec["child_name"] or ""
            adult_count_input.value = rec["adult_count"] or 1
            observer_input.value = rec["observer"] or ""
            if stage_label in (stage_select.options or []):
                stage_select.value = stage_label
            child_age_input.value = infer_age_by_grade(rec["grade"] or "")
            for domain, state in domain_states.items():
                domain_detail = detail_by_domain.get(domain)
                if not domain_detail:
                    continue
                state["year"].value = domain_detail.get("obs_year") or rec["obs_year"]
                state["month"].value = (
                    domain_detail.get("obs_month") or rec["obs_month"]
                )
                dates = [
                    domain_detail.get("date_1"),
                    domain_detail.get("date_2"),
                    domain_detail.get("date_3"),
                ]
                for i, date_input in enumerate(state["date_inputs"]):
                    date_input.value = (
                        dates[i].isoformat() if i < len(dates) and dates[i] else ""
                    )
                state["goals"].value = domain_detail.get("goals") or ""
                state["eval"].value = domain_detail.get("evaluation") or ""
                state["strategy"].value = domain_detail.get("support_strategy") or ""
                images = domain_detail.get("images") or []
                state["raw_images"] = [image["data"] for image in images]
                state["compressed"] = [_rebuild_compressed(image) for image in images]
                _render_domain_previews(state)
                for i, area in enumerate(state["desc_areas"]):
                    area.value = (
                        images[i].get("description") or "" if i < len(images) else ""
                    )
                stars_by_order = {
                    item["sort_order"]: item["stars"]
                    for item in domain_detail.get("indicators") or []
                }
                for indicator in state["indicators"]:
                    indicator["select"].value = stars_by_order.get(
                        indicator["sort_order"],
                        3,
                    )
            edit_state["record_id"] = rid
            edit_banner.set_text(f"✎ 正在编辑记录 ID：{rid}（保存将覆盖更新）")
            edit_banner.classes(remove="hidden")
            cancel_edit_btn.classes(remove="hidden")
            save_btn.set_text("覆盖保存")
        _advance_form_generation()
        show_info(f"已载入记录 {rid}，可修改后覆盖保存", ok=True)

    def trigger_load_for_edit(rid: int):
        _advance_form_generation()
        generation = form_generation[0]
        return do_load_for_edit(generation, rid)

    async def do_cancel_edit(generation: int, stage_label: str) -> None:
        if not await _require_bound_session():
            return
        if not _form_is_current(generation):
            return
        await render_domains(generation, stage_label)
        if not await _require_bound_session() or not _form_is_current(generation):
            return
        with _programmatic_form_update():
            edit_state["record_id"] = None
            edit_banner.classes(add="hidden")
            cancel_edit_btn.classes(add="hidden")
            save_btn.set_text("保存")
            child_name_input.value = ""
        _advance_form_generation()
        show_info("已退出编辑，可新建记录", ok=True)

    def trigger_cancel_edit(*_event_args: object):
        _advance_form_generation()
        generation = form_generation[0]
        stage_label = str(stage_select.value or default_stage)
        return do_cancel_edit(generation, stage_label)

    cancel_edit_btn.on("click", trigger_cancel_edit)

    # ── 历史记录区 ─────────────────────────────────────────────────
    selected_ids: set[int] = set()

    with ui.column().classes("w-full max-w-5xl mx-auto px-6 pb-10 gap-3"):
        ui.separator()
        ui.label("历史倾听记录").classes("text-lg font-semibold text-gray-700")
        with ui.row().classes("w-full gap-3 items-end flex-wrap"):
            filter_year = ui.number(
                label="筛选年", min=2020, max=2100, format="%d"
            ).classes("w-28")
            filter_month = ui.select(
                label="筛选月",
                options={0: "全部", **{m: str(m) for m in _MONTHS}},
                value=0,
            ).classes("w-28")
            filter_name = ui.input(label="幼儿姓名").classes("w-40")
            refresh_btn = ui.button("查询", icon="search").props("outline")
            batch_export_btn = ui.button(
                "批量按领域导出(zip)", icon="folder_zip"
            ).classes("bg-orange-500 text-white")
        history_container = ui.column().classes("w-full gap-2")

    for control in (filter_year, filter_month, filter_name):
        control.on("update:model-value", _invalidate_history)

    async def _show_detail(generation: int, rid: int) -> None:
        if not await _require_bound_session():
            return
        if not _history_is_current(generation):
            return
        async with AsyncSessionLocal() as session:
            detail = await load_record_detail(session, tenant_id, user_id, rid)
        if not await _require_bound_session() or not _history_is_current(generation):
            return
        if not detail:
            show_error("记录不存在")
            return
        rec = detail["record"]
        with ui.dialog() as dlg, ui.card().classes("max-w-3xl"):
            stage = format_stage_label(rec["grade"] or "", rec["term"] or "").strip("·")
            ui.label(
                f"{rec['child_name']}  {rec['obs_year']}年{rec['obs_month']}月  {stage}"
            ).classes("text-lg font-semibold")
            for dom in detail["domains"]:
                with ui.expansion(f"{dom['domain']}领域", icon="folder_open").classes(
                    "w-full"
                ):
                    ui.label(f"目标：{dom.get('goals') or '-'}").classes(
                        "text-sm whitespace-pre-wrap"
                    )
                    with ui.row().classes("gap-2 flex-wrap"):
                        for im in dom.get("images") or []:
                            if im.get("data"):
                                mime = im.get("mime_type") or "image/jpeg"
                                ui.image(
                                    f"data:{mime};base64,{base64.b64encode(im['data']).decode()}"
                                ).classes("w-24 h-24 object-cover rounded border")
                    for i, im in enumerate(dom.get("images") or []):
                        ui.label(
                            f"图{i + 1}描述：{im.get('description') or '-'}"
                        ).classes("text-xs text-gray-600 whitespace-pre-wrap")
                    stars = "，".join(
                        f"[{ind['sort_order']}]{'★' * int(ind['stars'])}"
                        for ind in dom.get("indicators") or []
                    )
                    ui.label(f"指标星级：{stars or '-'}").classes(
                        "text-xs text-gray-600"
                    )
                    ui.label(f"综合评价：{dom.get('evaluation') or '-'}").classes(
                        "text-sm whitespace-pre-wrap"
                    )
                    ui.label(f"支持策略：{dom.get('support_strategy') or '-'}").classes(
                        "text-sm whitespace-pre-wrap"
                    )
            ui.button("关闭", on_click=dlg.close).classes("mt-2")
        dlg.open()

    def trigger_show_detail(rid: int):
        generation = history_generation[0]
        return _show_detail(generation, rid)

    async def _reexport_combined(
        generation: int,
        rid: int,
        child_name: str,
        year: int,
        month: int,
    ) -> None:
        if not await _require_bound_session():
            return
        if not _history_is_current(generation):
            return
        try:
            async with AsyncSessionLocal() as session:
                detail = await load_record_detail(session, tenant_id, user_id, rid)
                if not await _require_bound_session() or not _history_is_current(
                    generation
                ):
                    return
                if not detail:
                    show_error("记录不存在")
                    return
                record, domains = to_export_payload(detail)
                data = export_combined(record, domains)
                fname = build_export_filename(
                    tenant_id,
                    user_id,
                    child_name or "幼儿",
                    year or 0,
                    month or 0,
                    "合并",
                )
                await save_export_record(
                    session,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    daily_plan_id=None,
                    file_name=fname,
                    file_path=f"exports/{fname}",
                    listening_record_id=rid,
                )
                await session.commit()
            if not await _require_bound_session() or not _history_is_current(
                generation
            ):
                return
            log_audit(
                "export_listening",
                tenant_id=tenant_id,
                user_id=user_id,
                file_name=fname,
                listening_record_id=rid,
                mode="combined",
            )
            ui.download(data, fname)
            show_info(f"导出成功：{fname}", ok=True)
        except Exception as ex:  # noqa: BLE001
            if not await _require_bound_session() or not _history_is_current(
                generation
            ):
                return
            logger.error("历史合并导出失败 error_type=%s", type(ex).__name__)
            show_error(f"导出失败：{type(ex).__name__}")

    async def _reexport_split(
        generation: int,
        rid: int,
        child_name: str,
        year: int,
        month: int,
    ) -> None:
        if not await _require_bound_session():
            return
        if not _history_is_current(generation):
            return
        try:
            async with AsyncSessionLocal() as session:
                detail = await load_record_detail(session, tenant_id, user_id, rid)
                if not await _require_bound_session() or not _history_is_current(
                    generation
                ):
                    return
                if not detail:
                    show_error("记录不存在")
                    return
                record, domains = to_export_payload(detail)
                files = export_split_by_domain(record, domains)
                zip_bytes = pack_domain_files_to_zip(files)
                zip_name = build_export_filename(
                    tenant_id,
                    user_id,
                    child_name or "幼儿",
                    year or 0,
                    month or 0,
                    "按领域",
                ).replace(".docx", ".zip")
                await save_export_record(
                    session,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    daily_plan_id=None,
                    file_name=zip_name,
                    file_path=f"exports/{zip_name}",
                    listening_record_id=rid,
                )
                await session.commit()
            if not await _require_bound_session() or not _history_is_current(
                generation
            ):
                return
            log_audit(
                "export_listening",
                tenant_id=tenant_id,
                user_id=user_id,
                file_name=zip_name,
                listening_record_id=rid,
                mode="split",
            )
            ui.download(zip_bytes, zip_name)
            show_info(f"导出成功：{zip_name}", ok=True)
        except Exception as ex:  # noqa: BLE001
            if not await _require_bound_session() or not _history_is_current(
                generation
            ):
                return
            logger.error("历史按领域导出失败 error_type=%s", type(ex).__name__)
            show_error(f"导出失败：{type(ex).__name__}")

    def trigger_reexport_combined(
        rid: int,
        child_name: str,
        year: int,
        month: int,
    ):
        generation = history_generation[0]
        owner = action_guard.claim("listening.history-export")
        if owner is None:
            return None
        return _run_claimed_action(
            "listening.history-export",
            owner,
            _reexport_combined(generation, rid, child_name, year, month),
        )

    def trigger_reexport_split(
        rid: int,
        child_name: str,
        year: int,
        month: int,
    ):
        generation = history_generation[0]
        owner = action_guard.claim("listening.history-export")
        if owner is None:
            return None
        return _run_claimed_action(
            "listening.history-export",
            owner,
            _reexport_split(generation, rid, child_name, year, month),
        )

    async def _delete_listening_record(
        generation: int,
        rid: int,
    ) -> None:
        if not await _require_bound_session():
            return
        if not _history_is_current(generation):
            return
        with ui.dialog() as dlg, ui.card():
            ui.label(
                "确定删除这条倾听记录吗？将一并删除其图片与指标，删除后无法恢复。"
            ).classes("text-base")
            with ui.row().classes("gap-3 mt-3"):
                ui.button("确认删除", on_click=lambda: dlg.submit("yes")).classes(
                    "bg-red-600 text-white"
                )
                ui.button("取消", on_click=lambda: dlg.submit("no"))
        if await dlg == "yes":
            if not await _require_bound_session() or not _history_is_current(
                generation
            ):
                return
            try:
                async with AsyncSessionLocal() as session:
                    async with AsyncSessionUnitOfWork(session):
                        await delete_images_by_record(session, tenant_id, user_id, rid)
                        await delete_indicator_results_by_record(
                            session, tenant_id, user_id, rid
                        )
                        await delete_domains_by_record(session, tenant_id, user_id, rid)
                        await delete_record(session, tenant_id, user_id, rid)
                if not await _require_bound_session() or not _history_is_current(
                    generation
                ):
                    return
                show_info("已删除", ok=True)
                refresh_operation = trigger_refresh_history()
                if refresh_operation is not None:
                    await refresh_operation
            except Exception as ex:  # noqa: BLE001
                if not await _require_bound_session() or not _history_is_current(
                    generation
                ):
                    return
                logger.error("删除倾听记录失败 error_type=%s", type(ex).__name__)
                show_error(f"删除失败：{type(ex).__name__}")

    def trigger_delete_listening_record(rid: int):
        generation = history_generation[0]
        owner = action_guard.claim("listening.history-write")
        if owner is None:
            return None
        return _run_claimed_action(
            "listening.history-write",
            owner,
            _delete_listening_record(generation, rid),
        )

    def _toggle_select(rid: int, checked: bool) -> None:
        if checked:
            selected_ids.add(rid)
        else:
            selected_ids.discard(rid)
        _advance_history_generation()

    def _build_history_row(rec) -> None:
        with ui.card().classes("w-full"):
            with ui.row().classes(
                "w-full justify-between items-center flex-wrap gap-2"
            ):
                with ui.row().classes("items-center gap-2"):
                    ui.checkbox(
                        on_change=lambda e, rid=rec.id: _toggle_select(
                            rid, bool(e.value)
                        )
                    )
                    ui.label(
                        format_record_summary(
                            rec.child_name,
                            rec.obs_year,
                            rec.obs_month,
                            rec.grade,
                            rec.term,
                            rec.observer,
                        )
                    ).classes("text-sm text-gray-700")
                with ui.row().classes("items-center gap-1"):
                    ui.button(
                        "详情",
                        icon="visibility",
                        on_click=lambda rid=rec.id: trigger_show_detail(rid),
                    ).props("size=sm flat")
                    ui.button(
                        "导出合并",
                        icon="download",
                        on_click=lambda rid=rec.id, nm=rec.child_name, y=rec.obs_year, m=rec.obs_month: (
                            trigger_reexport_combined(rid, nm, y, m)
                        ),
                    ).props("size=sm flat").classes("text-blue-600")
                    ui.button(
                        "按领域zip",
                        icon="folder_zip",
                        on_click=lambda rid=rec.id, nm=rec.child_name, y=rec.obs_year, m=rec.obs_month: (
                            trigger_reexport_split(rid, nm, y, m)
                        ),
                    ).props("size=sm flat").classes("text-blue-600")
                    ui.button(
                        "编辑",
                        icon="edit",
                        on_click=lambda rid=rec.id: trigger_load_for_edit(rid),
                    ).props("size=sm flat").classes("text-indigo-600")
                    ui.button(
                        "删除",
                        icon="delete",
                        on_click=lambda rid=rec.id: trigger_delete_listening_record(
                            rid
                        ),
                    ).props("size=sm flat").classes("text-red-500")

    async def refresh_history(
        generation: int,
        filter_year_value: int | None,
        filter_month_value: int | None,
        filter_name_value: str | None,
    ) -> None:
        if not await _require_bound_session():
            return
        if not _history_is_current(generation):
            return
        try:
            async with AsyncSessionLocal() as session:
                records = await list_records(
                    session,
                    tenant_id,
                    user_id,
                    limit=50,
                    offset=0,
                    obs_year=filter_year_value,
                    obs_month=filter_month_value,
                    child_name=filter_name_value,
                )
            if not await _require_bound_session() or not _history_is_current(
                generation
            ):
                return
            history_container.clear()
            selected_ids.clear()
            with history_container:
                if not records:
                    ui.label("暂无记录").classes("text-gray-400 text-sm")
                    return
                for rec in records:
                    _build_history_row(rec)
        except Exception as ex:  # noqa: BLE001
            if not await _require_bound_session() or not _history_is_current(
                generation
            ):
                return
            logger.error("加载倾听历史失败 error_type=%s", type(ex).__name__)
            with history_container:
                ui.label("加载历史失败").classes("text-red-500 text-sm")

    def trigger_refresh_history(*_event_args: object):
        _advance_history_generation()
        generation = history_generation[0]
        filter_year_value = int(filter_year.value) if filter_year.value else None
        filter_month_value = int(filter_month.value) or None
        filter_name_value = (filter_name.value or "").strip() or None
        return refresh_history(
            generation,
            filter_year_value,
            filter_month_value,
            filter_name_value,
        )

    async def do_batch_export(
        generation: int,
        ids: tuple[int, ...],
        year: int,
        month: int,
        owner: object,
    ) -> None:
        if not await _require_bound_session():
            return
        if not _history_is_current(generation):
            return
        if not ids:
            show_error("请先勾选要导出的幼儿记录")
            return
        batch_export_btn.props("loading=true")
        try:
            children = []
            async with AsyncSessionLocal() as session:
                for rid in ids:
                    detail = await load_record_detail(session, tenant_id, user_id, rid)
                    if not await _require_bound_session() or not _history_is_current(
                        generation
                    ):
                        return
                    if detail:
                        children.append(to_export_payload(detail))
            if not await _require_bound_session() or not _history_is_current(
                generation
            ):
                return
            if not children:
                show_error("所选记录无可导出内容")
                return
            files = export_batch_by_domain(children)
            zip_bytes = pack_domain_files_to_zip(files)
            zip_name = build_batch_export_filename(
                tenant_id,
                user_id,
                year,
                month,
                len(children),
            )
            async with AsyncSessionLocal() as session:
                await save_export_record(
                    session,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    daily_plan_id=None,
                    file_name=zip_name,
                    file_path=f"exports/{zip_name}",
                    listening_record_id=None,
                )
                await session.commit()
            if not await _require_bound_session() or not _history_is_current(
                generation
            ):
                return
            log_audit(
                "export_listening",
                tenant_id=tenant_id,
                user_id=user_id,
                file_name=zip_name,
                mode="batch",
                count=len(children),
            )
            ui.download(zip_bytes, zip_name)
            show_info(f"批量导出成功：{zip_name}（{len(children)} 人）", ok=True)
        except Exception as ex:  # noqa: BLE001
            if not await _require_bound_session() or not _history_is_current(
                generation
            ):
                return
            logger.error("批量按领域导出失败 error_type=%s", type(ex).__name__)
            show_error(f"批量导出失败：{type(ex).__name__}")
        finally:
            if (
                action_guard.owns("listening.history-export", owner)
                and await _require_bound_session()
            ):
                batch_export_btn.props(remove="loading")

    def trigger_batch_export(*_event_args: object):
        generation = history_generation[0]
        ids = tuple(sorted(selected_ids))
        year = int(filter_year.value) if filter_year.value else cur_year
        month = int(filter_month.value) or cur_month
        owner = action_guard.claim("listening.history-export")
        if owner is None:
            return None
        return _run_claimed_action(
            "listening.history-export",
            owner,
            do_batch_export(generation, ids, year, month, owner),
        )

    refresh_btn.on("click", trigger_refresh_history)
    batch_export_btn.on("click", trigger_batch_export)

    await render_domains(form_generation[0], str(stage_select.value or default_stage))
    await refresh_history(history_generation[0], None, None, None)
