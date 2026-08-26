"""敏感 NiceGUI 页面必须在长寿命回调中重验同一登录会话。"""

import ast
from pathlib import Path

import pytest


PAGE_DIR = Path(__file__).parents[1] / "app" / "ui" / "pages"


def _source(page: str) -> str:
    return (PAGE_DIR / page).read_text(encoding="utf-8")


def _async_function(page: str, name: str) -> ast.AsyncFunctionDef:
    matches = [
        node
        for node in ast.walk(ast.parse(_source(page)))
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name
    ]
    assert len(matches) == 1, f"expected one async function {name} in {page}"
    return matches[0]


def _normalized_function_source(page: str, name: str) -> str:
    return ast.unparse(_async_function(page, name))


def _assert_guard_between(
    source: str,
    *,
    after: str,
    guard: str,
    before: str,
) -> None:
    after_index = source.index(after)
    guard_index = source.index(guard, after_index + len(after))
    before_index = source.index(before, after_index + len(after))
    assert after_index < guard_index < before_index


def _assert_exception_handlers_start_with_guard(
    page: str,
    callback: str,
    guard: str,
) -> None:
    function = _async_function(page, callback)
    handlers: list[ast.ExceptHandler] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Try):
            continue
        body_has_await = any(
            isinstance(descendant, ast.Await)
            for statement in node.body
            for descendant in ast.walk(statement)
        )
        if body_has_await:
            handlers.extend(node.handlers)
    assert handlers
    for handler in handlers:
        assert handler.body
        first = ast.unparse(handler.body[0])
        assert first.startswith(f"if await {guard}() is None:"), (
            f"{page}:{handler.lineno} {callback} must revalidate before handling "
            "an async failure"
        )


@pytest.mark.parametrize(
    ("page", "page_function"),
    [
        ("settings.py", "settings_page"),
        ("profile.py", "profile_page"),
        ("prompt_mgmt.py", "prompt_mgmt_page"),
    ],
)
def test_page_entry_builds_trusted_session_and_only_projects_for_shell(
    page: str,
    page_function: str,
) -> None:
    source = _source(page)
    function_dump = ast.dump(_async_function(page, page_function))

    assert "get_current_user_or_redirect" not in source
    assert "require_current_ui_session" in function_dump
    assert "as_user_dict" in function_dump
    assert "require_bound_ui_session" in function_dump


@pytest.mark.parametrize(
    ("page", "function", "query", "guard", "render"),
    [
        (
            "settings.py",
            "settings_page",
            "ai_vision_record = await get_active_ai_key(",
            "await require_live_session()",
            "if semester:",
        ),
        (
            "profile.py",
            "profile_page",
            "current_user = await get_user_by_id(",
            "await require_live_session()",
            "current_display_name =",
        ),
        (
            "prompt_mgmt.py",
            "_build_task_panel",
            "versions = await list_versions(",
            "await require_live_session()",
            "initial_content =",
        ),
        (
            "home.py",
            "home_page",
            "class_cfg = await get_class_config(",
            "await _require_bound_session()",
            "async with app_shell(",
        ),
    ],
)
def test_initial_actor_scoped_reads_revalidate_exact_jti_before_rendering(
    page: str,
    function: str,
    query: str,
    guard: str,
    render: str,
) -> None:
    _assert_guard_between(
        _normalized_function_source(page, function),
        after=query,
        guard=guard,
        before=render,
    )


@pytest.mark.parametrize(
    ("page", "callback"),
    [
        ("profile.py", "save_display_name"),
        ("profile.py", "save_password"),
        ("prompt_mgmt.py", "save_version"),
        ("prompt_mgmt.py", "do_test"),
        ("prompt_mgmt.py", "rollback"),
    ],
)
def test_sensitive_callback_starts_with_exact_session_guard(
    page: str,
    callback: str,
) -> None:
    function = _async_function(page, callback)

    assert function.body
    assert "require_live_session" in ast.dump(function.body[0])


@pytest.mark.parametrize(
    ("page", "callback", "minimum_guard_calls"),
    [
        ("settings.py", "save_ai_key_handler", 2),
        ("settings.py", "verify_connection", 2),
        ("settings.py", "save_vision_key_handler", 2),
        ("settings.py", "verify_vision_connection", 2),
        ("prompt_mgmt.py", "save_version", 2),
        ("prompt_mgmt.py", "do_test", 4),
        ("prompt_mgmt.py", "rollback", 2),
    ],
)
def test_multistage_callback_revalidates_before_persisting_or_rendering_result(
    page: str,
    callback: str,
    minimum_guard_calls: int,
) -> None:
    function_dump = ast.dump(_async_function(page, callback))

    assert function_dump.count("id='require_live_session'") >= minimum_guard_calls


@pytest.mark.parametrize(
    ("callback", "query", "render"),
    [
        (
            "refresh_history",
            "await list_daily_plans_for_user(",
            "history_container.clear()",
        ),
        ("_load_draft", "await get_daily_plan_by_date(", "goal_area.value ="),
    ],
)
def test_daily_plan_db_reads_revalidate_exact_jti_before_rendering(
    callback: str,
    query: str,
    render: str,
) -> None:
    _assert_guard_between(
        _normalized_function_source("daily_plan.py", callback),
        after=query,
        guard="await _require_live_session()",
        before=render,
    )


@pytest.mark.parametrize(
    ("callback", "build", "write", "persist", "download"),
    [
        (
            "_export_word",
            "doc_bytes = export_daily_plan(",
            "file_path.write_bytes(doc_bytes)",
            "await save_export_record(",
            "ui.download(doc_bytes",
        ),
        (
            "_batch_export",
            "doc_bytes = export_batch_daily_plans(",
            "file_path.write_bytes(doc_bytes)",
            "await save_export_record(",
            "ui.download(doc_bytes",
        ),
    ],
)
def test_daily_plan_exports_revalidate_before_file_and_browser_side_effects(
    callback: str,
    build: str,
    write: str,
    persist: str,
    download: str,
) -> None:
    source = _normalized_function_source("daily_plan.py", callback)
    _assert_guard_between(
        source,
        after=build,
        guard="await _require_live_session()",
        before=write,
    )
    _assert_guard_between(
        source,
        after=persist,
        guard="await _require_live_session()",
        before=download,
    )


@pytest.mark.parametrize(
    ("callback", "render"),
    [
        ("reload_table", "state['rows'] ="),
        ("load_pending", "pending ="),
    ],
)
def test_user_admin_reads_revalidate_exact_jti_before_rendering(
    callback: str,
    render: str,
) -> None:
    _assert_guard_between(
        _normalized_function_source("user_admin.py", callback),
        after="await list_users_for_admin(",
        guard="await _require_live_admin()",
        before=render,
    )


@pytest.mark.parametrize(
    ("callback", "snapshots", "service_call"),
    [
        (
            "on_create",
            (
                "username = username_input.value",
                "password = password_input.value",
                "role = role_select.value",
            ),
            "await create_user_by_admin(",
        ),
        (
            "on_set_active",
            (
                "target_user_value = target_user_select.value",
                "target_user_id = int(target_user_value)",
            ),
            "await set_user_active_by_admin(",
        ),
        (
            "on_reset_password",
            (
                "target_user_value = target_user_select.value",
                "new_password = reset_password_input.value",
                "target_user_id = int(target_user_value)",
            ),
            "await reset_user_password_by_admin(",
        ),
    ],
)
def test_user_admin_freezes_action_payload_before_first_await(
    callback: str,
    snapshots: tuple[str, ...],
    service_call: str,
) -> None:
    source = _normalized_function_source("user_admin.py", callback)
    first_await_index = source.index("await ")
    db_context_index = source.index("async with AsyncSessionLocal()")
    for snapshot in snapshots:
        assert source.index(snapshot) < first_await_index < db_context_index
    call_index = source.index(service_call, db_context_index)
    post_call_guard = source.index("await _require_live_admin()", call_index)
    assert ".value" not in source[call_index:post_call_guard]


@pytest.mark.parametrize(
    "callback",
    [
        "_do_split",
        "_gen_daily_reflection",
        "_save_draft",
        "_delete_draft",
        "_delete_plan",
        "_export_word",
        "_batch_export",
    ],
)
def test_daily_plan_async_errors_revalidate_before_ui_writeback(callback: str) -> None:
    _assert_exception_handlers_start_with_guard(
        "daily_plan.py",
        callback,
        "_require_live_session",
    )


@pytest.mark.parametrize(
    "callback",
    ["on_create", "on_set_active", "on_reset_password", "_approve"],
)
def test_user_admin_async_errors_revalidate_before_ui_writeback(callback: str) -> None:
    _assert_exception_handlers_start_with_guard(
        "user_admin.py",
        callback,
        "_require_live_admin",
    )


@pytest.mark.parametrize(
    "callback", ["on_create", "on_set_active", "on_reset_password"]
)
def test_user_admin_unexpected_failures_are_closed_and_redacted(callback: str) -> None:
    function = _async_function("user_admin.py", callback)
    generic_handlers = [
        handler
        for node in ast.walk(function)
        if isinstance(node, ast.Try)
        for handler in node.handlers
        if isinstance(handler.type, ast.Name) and handler.type.id == "Exception"
    ]
    assert len(generic_handlers) == 1
    rendered = ast.unparse(generic_handlers[0])
    assert "str(" not in rendered
    assert "exc_info" not in rendered


@pytest.mark.parametrize(
    ("page", "callback"),
    [
        ("profile.py", "save_display_name"),
        ("profile.py", "save_password"),
        ("prompt_mgmt.py", "save_version"),
        ("prompt_mgmt.py", "do_test"),
        ("prompt_mgmt.py", "rollback"),
    ],
)
def test_sensitive_page_async_errors_revalidate_before_ui_writeback(
    page: str,
    callback: str,
) -> None:
    _assert_exception_handlers_start_with_guard(
        page,
        callback,
        "require_live_session",
    )


def test_daily_plan_export_errors_do_not_render_raw_exception_text() -> None:
    for callback in ("_gen_all_daily", "_export_word", "_batch_export"):
        source = _normalized_function_source("daily_plan.py", callback)
        assert "{e}" not in source
        assert "{res}" not in source
        assert "str(e)" not in source


@pytest.mark.parametrize(
    "callback",
    ["_do_split", "_gen_all_daily", "_gen_daily_reflection"],
)
def test_daily_plan_does_not_render_untrusted_ai_error_messages(
    callback: str,
) -> None:
    source = _normalized_function_source("daily_plan.py", callback)
    assert ".message" not in source


def test_daily_plan_history_delete_does_not_render_raw_exception_text() -> None:
    source = _normalized_function_source("daily_plan.py", "_delete_plan")
    assert "{ex}" not in source
    assert "str(ex)" not in source


@pytest.mark.parametrize(
    ("page", "callback"),
    [("register.py", "do_register"), ("one_on_one_listening.py", "do_apply_bulk")],
)
def test_generic_ui_failures_do_not_render_or_log_exception_bodies(
    page: str,
    callback: str,
) -> None:
    function = _async_function(page, callback)
    generic_handlers = [
        handler
        for node in ast.walk(function)
        if isinstance(node, ast.Try)
        for handler in node.handlers
        if isinstance(handler.type, ast.Name) and handler.type.id == "Exception"
    ]
    assert len(generic_handlers) == 1
    rendered = ast.unparse(generic_handlers[0])
    assert "exc_info" not in rendered
    assert "str(" not in rendered
    assert "{e}" not in rendered
    assert "{ex}" not in rendered


def test_daily_plan_history_delete_only_clears_same_selection_generation() -> None:
    source = _normalized_function_source("daily_plan.py", "_delete_plan")
    assert "selected_target = _capture_plan_target()" in source
    capture_index = source.index("selected_target = _capture_plan_target()")
    dialog_index = source.index("with ui.dialog()")
    binding = source[capture_index:dialog_index]
    assert "selected_target.selected_date != p.plan_date" in binding
    assert "selected_target.plan_id != p.id" in binding
    assert "selected_target.revision != p.revision" in binding
    assert "selected_target = None" in binding
    _assert_guard_between(
        source,
        after="await delete_daily_plan(",
        guard="_is_current_plan_target(selected_target)",
        before="state['loaded_plan_id'] = None",
    )


@pytest.mark.parametrize(
    ("callback", "snapshots", "operation"),
    [
        (
            "_do_split",
            ("target = _capture_plan_target()", "raw = ", "grade = "),
            "async with AsyncSessionLocal()",
        ),
        (
            "_gen_all_daily",
            (
                "target = _capture_plan_target()",
                "base_ctx = {",
                "indoor_areas = ",
                "outdoor_content = ",
            ),
            "await is_near_holiday(",
        ),
        (
            "_gen_daily_reflection",
            ("target = _capture_plan_target()", "context = {"),
            "async with AsyncSessionLocal()",
        ),
        (
            "_save_draft",
            ("target = _capture_plan_target()", "save_payload = "),
            "agent_panel.plan_changed(d)",
        ),
        (
            "_delete_draft",
            (
                "target = _capture_plan_target()",
                "deleting_date = ",
                "deleting_plan_id = ",
                "deleting_revision = ",
            ),
            "with ui.dialog()",
        ),
        (
            "_export_word",
            ("target = _capture_plan_target()",),
            "async with AsyncSessionLocal()",
        ),
    ],
)
def test_daily_plan_click_target_and_payload_are_frozen_before_auth_await(
    callback: str,
    snapshots: tuple[str, ...],
    operation: str,
) -> None:
    source = _normalized_function_source("daily_plan.py", callback)
    auth_await = source.index("await _require_live_session()")
    for snapshot in snapshots:
        assert source.index(snapshot) < auth_await
    target_guard = source.index("_is_current_plan_target(target)", auth_await)
    assert auth_await < target_guard < source.index(operation, target_guard)


def test_daily_plan_batch_range_is_frozen_and_parsed_before_auth_await() -> None:
    source = _normalized_function_source("daily_plan.py", "_batch_export")
    auth_await = source.index("await _require_live_session()")
    for snapshot in (
        "start_str = batch_start_input.value",
        "end_str = batch_end_input.value",
        "start_date = datetime.strptime(",
        "end_date = datetime.strptime(",
    ):
        assert source.index(snapshot) < auth_await


def test_agent_run_freezes_intent_and_scope_before_auth_await() -> None:
    component_path = PAGE_DIR.parent / "components" / "agent_draft.py"
    component_tree = ast.parse(component_path.read_text(encoding="utf-8"))
    run_functions = [
        node
        for node in ast.walk(component_tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_run"
    ]
    assert len(run_functions) == 1
    run_source = ast.unparse(run_functions[0])
    auth_await = run_source.index("await self._authorize_operation()")
    assert run_source.index("operation_snapshot = ") < auth_await
    assert run_source.index("intent = ") < auth_await
    assert (
        run_source.index(
            "self._controller.snapshot is not operation_snapshot",
            auth_await,
        )
        > auth_await
    )

    authorize_source = _normalized_function_source(
        "daily_plan.py",
        "_authorize_agent_operation",
    )
    auth_await = authorize_source.index("await _require_live_session()")
    assert authorize_source.index("captured_selection = ") < auth_await
    identity_check = authorize_source.index(
        "selection_state['current'] is captured_selection",
        auth_await,
    )
    assert auth_await < identity_check


def test_daily_plan_save_rejects_stale_ui_target_before_state_writeback() -> None:
    source = _normalized_function_source("daily_plan.py", "_save_draft")
    payload_index = source.index("save_payload = {")
    db_context_index = source.index("async with AsyncSessionLocal()")
    assert payload_index < db_context_index
    assert "**save_payload" in source
    _assert_guard_between(
        source,
        after="saved_plan = await save_daily_plan(",
        guard="_is_current_plan_target(",
        before="state['loaded_plan_id'] = saved_plan.id",
    )


def test_daily_plan_delete_binds_dialog_and_writeback_to_same_ui_target() -> None:
    source = _normalized_function_source("daily_plan.py", "_delete_draft")
    _assert_guard_between(
        source,
        after="result = await dlg",
        guard="_is_current_plan_target(",
        before="await delete_daily_plan(",
    )
    _assert_guard_between(
        source,
        after="await delete_daily_plan(",
        guard="_is_current_plan_target(",
        before="for area in (",
    )


@pytest.mark.parametrize(
    ("callback", "awaited_work", "writeback"),
    [
        (
            "_do_split",
            "result = await process_lesson_plan(",
            "goal_area.value = result.activity_goal",
        ),
        (
            "_gen_all_daily",
            "results = await asyncio.gather(",
            "for (task_type, _extra, area, msg, name), res in zip(",
        ),
        (
            "_gen_daily_reflection",
            "content = await generate_activity_content(",
            "daily_reflection_area.value = content",
        ),
        (
            "_export_word",
            "plan = await get_daily_plan_by_date(",
            "doc_bytes = export_daily_plan(",
        ),
    ],
)
def test_date_scoped_async_results_are_discarded_after_selection_changes(
    callback: str,
    awaited_work: str,
    writeback: str,
) -> None:
    source = _normalized_function_source("daily_plan.py", callback)
    _assert_guard_between(
        source,
        after=awaited_work,
        guard="_is_current_plan_target(",
        before=writeback,
    )
