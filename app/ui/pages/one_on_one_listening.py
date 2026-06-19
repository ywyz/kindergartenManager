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

import asyncio
import base64
import io
import zipfile
from datetime import date

from nicegui import ui

from app.core.database import AsyncSessionLocal
from app.core.exceptions import AiCallError, AiParseError, AppError, ConfigError
from app.core.logging import get_logger
from app.core.user_context import get_current_user
from app.integration.holiday_client.client import is_holiday
from app.integration.image_processing import compress_image
from app.integration.image_storage.blob_backend import BlobImageStorage
from app.integration.word_export.listening_exporter import (
    export_combined,
    export_split_by_domain,
)
from app.repository.class_repository import get_class_config
from app.repository.export_repository import save_export_record
from app.repository.indicator_repository import list_available_stages, list_indicators
from app.repository.semester_repository import get_active_semester
from app.service.date_service import pick_three_workdays
from app.service.listening_service import (
    generate_domain_content,
    save_record_with_all,
)
from app.ui.components.app_shell import get_display_name, render_shell

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


def validate_image_count(count: int) -> bool:
    """校验单领域图片数量是否在 1~3。"""
    return 1 <= count <= 3


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
    return f"{tenant_id}_{user_id}_{safe_name}_{year}年{month}月_一对一倾听_{suffix}.docx"


def _parse_iso_date(value: str | None) -> date | None:
    """容错解析 YYYY-MM-DD，失败返回 None。"""
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        return None


async def _auto_pick_workdays(year: int, month: int) -> list[date]:
    """并发查询当月前三周工作日的节假日状态，返回 3 个工作日。"""
    import calendar

    num_days = calendar.monthrange(year, month)[1]
    weekday_dates = [
        date(year, month, d)
        for d in range(1, min(num_days, 21) + 1)
        if date(year, month, d).weekday() < 5
    ]
    try:
        results = await asyncio.gather(
            *[is_holiday(d) for d in weekday_dates], return_exceptions=True
        )
        holiday_set = {d for d, r in zip(weekday_dates, results) if r is True}
    except Exception:  # noqa: BLE001 — 节假日不可用时降级
        holiday_set = set()
    return pick_three_workdays(year, month, is_holiday=lambda d: d in holiday_set)


# ─── 页面路由 ──────────────────────────────────────────────────────────────────


@ui.page("/one-on-one-listening")
async def one_on_one_listening_page() -> None:
    user = get_current_user()
    tenant_id: int = user["tenant_id"]
    user_id: int = int(user["sub"])

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

    # 学段下拉选项
    stage_labels = [format_stage_label(g, t) for g, t in stages] or ["小班·下学期"]
    default_stage = format_stage_label(grade_default or "小班", term_default or "下学期")
    if default_stage not in stage_labels:
        default_stage = stage_labels[0]

    await render_shell(user, active="one-on-one-listening")

    observer_default = get_display_name(user)
    cur_year, cur_month = default_year_month()

    # 每领域状态：raw_images / compressed / 各 widget 引用 / 指标行
    domain_states: dict[str, dict] = {}

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
                year_input = ui.number(label="观察年", value=cur_year, min=2020, max=2100,
                                       format="%d").classes("w-28")
                month_select = ui.select(label="观察月", options=_MONTHS, value=cur_month).classes("w-24")
                child_name_input = ui.input(label="幼儿姓名", placeholder="单个幼儿").classes("flex-1 min-w-40")
                adult_count_input = ui.number(label="成人数目", value=1, min=1).classes("w-28")

            with ui.row().classes("w-full gap-4 flex-wrap items-end"):
                stage_select = ui.select(
                    label="年级·学期（指标版本）", options=stage_labels, value=default_stage,
                ).classes("w-52")
                child_age_input = ui.input(
                    label="幼儿年龄", value=infer_age_by_grade(grade_default or "小班"),
                ).classes("w-28")
                observer_input = ui.input(label="观察者", value=observer_default).classes("flex-1 min-w-40")

            with ui.row().classes("w-full gap-3 items-center"):
                autopick_btn = ui.button("自动选取工作日（填入各领域）", icon="event_available").props("outline")
                ui.label("按上方年月，从前三周各取一个工作日（排除法定节假日）").classes(
                    "text-xs text-gray-400"
                )

        domains_container = ui.column().classes("w-full gap-3")

        # ── 操作按钮 ──────────────────────────────────────────────
        with ui.row().classes("w-full gap-3 justify-end mt-2"):
            save_btn = ui.button("保存", icon="save").classes("bg-blue-600 text-white")
            export_combined_btn = ui.button("导出合并 Word", icon="download").classes("bg-orange-500 text-white")
            export_split_btn = ui.button("导出按领域(zip)", icon="folder_zip").props("outline")

    # ── 领域分区渲染 ───────────────────────────────────────────────
    def _on_grade_age_sync() -> None:
        g, _t = parse_stage_label(stage_select.value or default_stage)
        child_age_input.value = infer_age_by_grade(g)

    async def render_domains() -> None:
        domains_container.clear()
        domain_states.clear()
        grade, term = parse_stage_label(stage_select.value or default_stage)
        async with AsyncSessionLocal() as session:
            catalog_by_domain = {
                d: await list_indicators(session, tenant_id, grade, term, d)
                for d in _UI_DOMAINS
            }
        with domains_container:
            for domain in _UI_DOMAINS:
                _build_domain_section(domain, catalog_by_domain.get(domain, []))

    def _build_domain_section(domain: str, catalog: list) -> None:
        st: dict = {"raw_images": [], "compressed": None, "desc_areas": [],
                    "date_inputs": [], "indicators": []}
        domain_states[domain] = st

        with ui.expansion(f"{domain}领域", icon="folder_open").classes(
            "w-full border rounded-lg"
        ).props("header-class=text-indigo-700 font-semibold"):
            with ui.column().classes("w-full p-2 gap-3"):
                # 年月 + 日期
                with ui.row().classes("w-full gap-3 flex-wrap items-end"):
                    st["year"] = ui.number(label="年", value=cur_year, min=2020, max=2100,
                                           format="%d").classes("w-24")
                    st["month"] = ui.select(label="月", options=_MONTHS, value=cur_month).classes("w-20")
                    for i in range(3):
                        st["date_inputs"].append(
                            ui.input(label=f"日期{i+1}", placeholder="YYYY-MM-DD").classes("w-40")
                        )

                # 图片上传
                with ui.row().classes("w-full gap-4 items-center"):
                    count_label = ui.label("已上传：0 张").classes("text-gray-500 text-sm")
                    preview_row = ui.row().classes("gap-2 flex-wrap")
                st["count_label"] = count_label
                st["preview_row"] = preview_row

                async def _on_upload(e, d=domain) -> None:
                    s = domain_states[d]
                    if len(s["raw_images"]) >= 3:
                        show_error(f"{d}领域最多 3 张图片")
                        return
                    data = await e.file.read() if hasattr(e, "file") else e.content.read()
                    s["raw_images"].append(data)
                    s["compressed"] = None  # 新图需重新生成
                    s["count_label"].set_text(f"已上传：{len(s['raw_images'])} 张")
                    with s["preview_row"]:
                        ui.image(f"data:image/jpeg;base64,{base64.b64encode(data).decode()}").classes(
                            "w-20 h-20 object-cover rounded border"
                        )

                ui.upload(on_upload=_on_upload, auto_upload=True, multiple=True).props(
                    "accept=image/*"
                ).classes("w-full")

                gen_btn = ui.button(f"生成{domain}领域", icon="auto_awesome").classes(
                    "bg-indigo-600 text-white"
                )
                st["gen_btn"] = gen_btn

                st["goals"] = ui.textarea(label="目标（1~2 点）").classes("w-full")
                with ui.column().classes("w-full gap-1"):
                    ui.label("图片描述（一对一倾听记录）").classes("text-sm text-gray-600")
                    for i in range(3):
                        st["desc_areas"].append(
                            ui.textarea(label=f"图{i+1}描述").classes("w-full")
                        )

                # 指标星级
                with ui.expansion(f"二级指标评定（{len(catalog)} 项）", icon="star").classes("w-full"):
                    if not catalog:
                        ui.label("未找到该领域指标，请检查年级·学期配置").classes(
                            "text-amber-600 text-sm"
                        )
                    for cat in catalog:
                        with ui.row().classes("w-full items-center gap-2 border-b py-1"):
                            ui.label(f"[{cat.sort_order}] {cat.level2_name}").classes(
                                "flex-1 text-xs text-gray-700"
                            )
                            sel = ui.select(
                                options={1: "★", 2: "★★", 3: "★★★"}, value=3,
                            ).classes("w-24")
                            st["indicators"].append(
                                {"catalog_id": cat.id, "sort_order": cat.sort_order, "select": sel}
                            )

                st["eval"] = ui.textarea(label="综合评价（约 200 字）").classes("w-full")
                st["strategy"] = ui.textarea(label="支持策略（约 200 字）").classes("w-full")

        async def _do_generate(d=domain) -> None:
            s = domain_states[d]
            s["gen_btn"].props("loading=true")
            try:
                if not validate_image_count(len(s["raw_images"])):
                    show_error(f"{d}领域请先上传 1~3 张绘画照片")
                    return
                grade, term = parse_stage_label(stage_select.value or default_stage)
                ctx = {
                    "grade": grade, "term": term,
                    "child_name": child_name_input.value,
                    "child_age": child_age_input.value,
                }
                show_info(f"⏳ 正在生成{d}领域……")
                async with AsyncSessionLocal() as session:
                    result = await generate_domain_content(
                        session=session, tenant_id=tenant_id, user_id=user_id,
                        domain=d, images=s["raw_images"], context=ctx,
                    )
                s["compressed"] = result["compressed_images"]
                s["goals"].value = result["goals"]
                descs = result["image_descriptions"]
                for i, area in enumerate(s["desc_areas"]):
                    area.value = descs[i] if i < len(descs) else ""
                stars_by_order = {r["sort_order"]: r["stars"] for r in result["indicator_results"]}
                for ind in s["indicators"]:
                    ind["select"].value = stars_by_order.get(ind["sort_order"], 3)
                s["eval"].value = result["evaluation"]
                s["strategy"].value = result["support_strategy"]
                show_info(f"{d}领域生成成功，请检查后保存", ok=True)
            except ConfigError as ex:
                show_error(f"配置错误：{ex.message}")
            except (AiCallError, AiParseError) as ex:
                show_error(f"AI 调用失败：{ex.message}")
            except AppError as ex:
                show_error(f"生成失败：{ex.message}")
            except Exception as ex:  # noqa: BLE001
                logger.error("生成倾听领域失败", exc_info=ex)
                show_error(f"生成失败：{ex}")
            finally:
                s["gen_btn"].props(remove="loading")

        gen_btn.on("click", _do_generate)

    # ── 自动选取工作日 ─────────────────────────────────────────────
    async def do_autopick() -> None:
        autopick_btn.props("loading=true")
        try:
            year = int(year_input.value or cur_year)
            month = int(month_select.value or cur_month)
            workdays = await _auto_pick_workdays(year, month)
            for st in domain_states.values():
                st["year"].value = year
                st["month"].value = month
                for i, di in enumerate(st["date_inputs"]):
                    di.value = workdays[i].isoformat() if i < len(workdays) else ""
            if len(workdays) < 3:
                show_info(f"仅找到 {len(workdays)} 个工作日，请手动补全", ok=False)
            else:
                show_info("已自动填入各领域工作日，可手动调整", ok=True)
        except Exception as ex:  # noqa: BLE001
            logger.error("自动选取工作日失败", exc_info=ex)
            show_error(f"自动选取失败：{ex}")
        finally:
            autopick_btn.props(remove="loading")

    autopick_btn.on("click", do_autopick)
    stage_select.on("update:model-value", lambda _e: (_on_grade_age_sync(), None))
    stage_select.on("update:model-value", lambda _e: render_domains())

    def _build_domain_payload(domain: str) -> dict | None:
        """从领域 widget 状态构建完整 payload（保存 + 导出共用）。返回 None 表示该领域无内容。"""
        st = domain_states.get(domain)
        if not st:
            return None
        compressed = st.get("compressed")
        if compressed is None and st["raw_images"]:
            compressed = [compress_image(b) for b in st["raw_images"]]
            st["compressed"] = compressed
        compressed = compressed or []
        descriptions = [a.value or "" for a in st["desc_areas"]][: len(compressed)]
        # 无图片且无文本则视为空领域
        has_content = bool(compressed) or bool((st["goals"].value or "").strip())
        if not has_content:
            return None
        indicator_results = [
            {"catalog_id": ind["catalog_id"], "sort_order": ind["sort_order"],
             "stars": int(ind["select"].value or 3)}
            for ind in st["indicators"]
        ]
        images = [(compressed[i].data, descriptions[i] if i < len(descriptions) else "")
                  for i in range(len(compressed))]
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
            "tenant_id": tenant_id, "user_id": user_id,
            "obs_year": int(year_input.value or cur_year),
            "obs_month": int(month_select.value or cur_month),
            "grade": grade or None, "term": term or None,
            "class_name": class_name_default or None,
            "observer": observer_input.value or None,
            **record,
        }
        domains = [p for d in _UI_DOMAINS if (p := _build_domain_payload(d))]
        return record_full, domains

    async def do_save() -> None:
        save_btn.props("loading=true")
        try:
            record_full, domains = _collect()
            if not record_full["child_name"]:
                show_error("请填写幼儿姓名")
                return
            if not domains:
                show_error("请至少为一个领域上传图片并生成内容")
                return
            async with AsyncSessionLocal() as session:
                rid = await save_record_with_all(
                    session, record_data=record_full, domains=domains,
                    storage=BlobImageStorage(),
                )
            show_info(f"保存成功（记录 ID：{rid}）", ok=True)
        except Exception as ex:  # noqa: BLE001
            logger.error("保存倾听记录失败", exc_info=ex)
            show_error(f"保存失败：{ex}")
        finally:
            save_btn.props(remove="loading")

    save_btn.on("click", do_save)

    def _export_record_dict() -> dict:
        return {
            "child_name": (child_name_input.value or "").strip(),
            "adult_count": int(adult_count_input.value or 1),
            "child_age": child_age_input.value or None,
        }

    async def do_export_combined() -> None:
        export_combined_btn.props("loading=true")
        try:
            _record_full, domains = _collect()
            if not domains:
                show_error("没有可导出的领域内容，请先生成")
                return
            data = export_combined(_export_record_dict(), domains)
            fname = build_export_filename(
                tenant_id, user_id, child_name_input.value or "幼儿",
                int(year_input.value or cur_year), int(month_select.value or cur_month), "合并",
            )
            async with AsyncSessionLocal() as session:
                await save_export_record(
                    session, tenant_id=tenant_id, user_id=user_id,
                    daily_plan_id=None, file_name=fname, file_path=f"exports/{fname}",
                )
                await session.commit()
            ui.download(data, fname)
            show_info(f"导出成功：{fname}", ok=True)
        except Exception as ex:  # noqa: BLE001
            logger.error("导出合并失败", exc_info=ex)
            show_error(f"导出失败：{ex}")
        finally:
            export_combined_btn.props(remove="loading")

    async def do_export_split() -> None:
        export_split_btn.props("loading=true")
        try:
            _record_full, domains = _collect()
            if not domains:
                show_error("没有可导出的领域内容，请先生成")
                return
            files = export_split_by_domain(_export_record_dict(), domains)
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for domain, content in files.items():
                    zf.writestr(f"{domain}.docx", content)
            zip_name = build_export_filename(
                tenant_id, user_id, child_name_input.value or "幼儿",
                int(year_input.value or cur_year), int(month_select.value or cur_month), "按领域",
            ).replace(".docx", ".zip")
            ui.download(buf.getvalue(), zip_name)
            show_info(f"导出成功：{zip_name}", ok=True)
        except Exception as ex:  # noqa: BLE001
            logger.error("导出按领域失败", exc_info=ex)
            show_error(f"导出失败：{ex}")
        finally:
            export_split_btn.props(remove="loading")

    export_combined_btn.on("click", do_export_combined)
    export_split_btn.on("click", do_export_split)

    await render_domains()
