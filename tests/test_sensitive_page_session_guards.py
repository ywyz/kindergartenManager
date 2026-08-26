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


def _sync_function(page: str, name: str) -> ast.FunctionDef:
    matches = [
        node
        for node in ast.walk(ast.parse(_source(page)))
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    assert len(matches) == 1, f"expected one sync function {name} in {page}"
    return matches[0]


def _normalized_function_source(page: str, name: str) -> str:
    return ast.unparse(_async_function(page, name))


def _bound_capture_source(
    page: str,
    trigger_name: str,
    callback_name: str,
) -> tuple[str, str]:
    tree = ast.parse(_source(page))
    assignments = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == trigger_name
            for target in node.targets
        )
    ]
    assert len(assignments) == 1, f"expected one bound trigger {trigger_name}"
    binding = assignments[0].value
    assert isinstance(binding, ast.Call)
    assert isinstance(binding.func, ast.Attribute) and binding.func.attr == "bind"
    keywords = {keyword.arg: keyword.value for keyword in binding.keywords}
    assert ast.unparse(keywords["run"]) == callback_name

    capture = keywords["capture"]
    capture_source = ast.unparse(capture)
    if isinstance(capture, ast.Name):
        capture_source += "\n" + ast.unparse(_sync_function(page, capture.id))
    return ast.unparse(binding), capture_source


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
        first = handler.body[0]
        guarded = isinstance(first, ast.If) and any(
            isinstance(node, ast.Await)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == guard
            for node in ast.walk(first.test)
        )
        assert guarded and first.body and isinstance(first.body[0], ast.Return), (
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
def test_sensitive_callback_has_no_await_before_exact_session_guard(
    page: str,
    callback: str,
) -> None:
    source = _normalized_function_source(page, callback)

    assert source.index("await ") == source.index("await require_live_session()")


@pytest.mark.parametrize(
    ("page", "trigger", "snapshots"),
    [
        (
            "settings.py",
            "trigger_save_ai_key",
            (
                "ai_url_input.value.strip()",
                "ai_model_input.value.strip()",
                "ai_key_input.value.strip()",
                "_current_masked[0]",
            ),
        ),
        (
            "settings.py",
            "trigger_save_vision_key",
            (
                "vision_url_input.value.strip()",
                "vision_model_input.value.strip()",
                "vision_key_input.value.strip()",
                "_vision_masked[0]",
            ),
        ),
        (
            "settings.py",
            "trigger_save_db_config",
            (
                "db_mode_radio.value",
                "db_host_input.value.strip()",
                "db_port_input.value.strip()",
                "db_user_input.value.strip()",
                "db_pass_input.value",
                "db_name_input.value.strip()",
            ),
        ),
        (
            "settings.py",
            "trigger_save_port",
            ("port_input.value",),
        ),
        (
            "profile.py",
            "trigger_save_display_name",
            ("display_name_input.value.strip()",),
        ),
        (
            "profile.py",
            "trigger_save_password",
            (
                "old_pwd_input.value",
                "new_pwd_input.value",
                "new_pwd2_input.value",
            ),
        ),
        (
            "prompt_mgmt.py",
            "trigger_save_version",
            ("content_area.value.strip()",),
        ),
        (
            "prompt_mgmt.py",
            "trigger_test",
            (
                "content_area.value.strip()",
                "test_input.value",
                "test_grade_select.value",
            ),
        ),
    ],
)
def test_sensitive_callback_uses_a_synchronous_click_snapshot(
    page: str,
    trigger: str,
    snapshots: tuple[str, ...],
) -> None:
    source = ast.unparse(_sync_function(page, trigger))

    for snapshot in snapshots:
        assert snapshot in source
    assert "await " not in source
    assert f"on_click={trigger}" in _source(page)


@pytest.mark.parametrize(
    ("page", "callback", "awaited_work", "writeback"),
    [
        (
            "settings.py",
            "save_ai_key_handler",
            "await save_ai_key(",
            "ai_key_input.value = masked",
        ),
        (
            "settings.py",
            "save_vision_key_handler",
            "await save_ai_key(",
            "vision_key_input.value = masked",
        ),
        (
            "profile.py",
            "save_display_name",
            "await update_profile_display_name(",
            "display_msg.set_text('✓ 显示名已保存')",
        ),
        (
            "profile.py",
            "save_password",
            "await change_password(",
            "pwd_msg.set_text('✓ 密码已修改')",
        ),
        (
            "prompt_mgmt.py",
            "save_version",
            "await save_new_version(",
            "msg_label.set_text(",
        ),
    ],
)
def test_sensitive_write_revalidates_after_await_before_success_writeback(
    page: str,
    callback: str,
    awaited_work: str,
    writeback: str,
) -> None:
    _assert_guard_between(
        _normalized_function_source(page, callback),
        after=awaited_work,
        guard="await require_live_session()",
        before=writeback,
    )


@pytest.mark.parametrize(
    ("handler_name", "scope_name", "payload_type", "controls"),
    [
        (
            "save_semester",
            "semester_operations",
            "_SemesterPayload",
            (
                "semester_name_input.value.strip()",
                "start_date_input.value.strip()",
                "end_date_input.value.strip()",
            ),
        ),
        (
            "save_class",
            "class_operations",
            "_ClassPayload",
            (
                "class_name_input.value.strip()",
                "grade_select.value",
                "teacher_name_input.value.strip()",
                "indoor_areas_input.value.strip()",
                "outdoor_content_input.value.strip()",
            ),
        ),
    ],
)
def test_settings_write_uses_synchronous_bound_operation_capture(
    handler_name: str,
    scope_name: str,
    payload_type: str,
    controls: tuple[str, ...],
) -> None:
    page = _async_function("settings.py", "settings_page")
    assignments = [
        node
        for node in ast.walk(page)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == handler_name
            for target in node.targets
        )
    ]

    assert len(assignments) == 1
    binding = ast.unparse(assignments[0].value)
    assert binding.startswith(f"{scope_name}.bind(")
    assert f"capture=lambda: {payload_type}(" in binding
    for control in controls:
        assert control in binding


def test_settings_independent_forms_use_independent_operation_scopes() -> None:
    page = _async_function("settings.py", "settings_page")
    assignments = {
        target.id: ast.unparse(node.value)
        for node in ast.walk(page)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id in {"save_semester", "save_class"}
    }

    assert assignments["save_semester"].startswith("semester_operations.bind(")
    assert assignments["save_class"].startswith("class_operations.bind(")
    assert "slot='semester.save'" in assignments["save_semester"]
    assert "slot='class.save'" in assignments["save_class"]


@pytest.mark.parametrize(
    (
        "trigger_name",
        "callback_name",
        "generation_name",
        "owner_name",
        "current_check",
        "invalidate_name",
        "controls",
    ),
    [
        (
            "trigger_save_db_config",
            "_save_db_config",
            "db_config_generation",
            "db_config_owner",
            "_db_config_operation_is_current",
            "_invalidate_db_config",
            (
                "db_mode_radio",
                "db_host_input",
                "db_port_input",
                "db_user_input",
                "db_pass_input",
                "db_name_input",
            ),
        ),
        (
            "trigger_save_port",
            "_save_port",
            "port_generation",
            "port_owner",
            "_port_operation_is_current",
            "_invalidate_port",
            ("port_input",),
        ),
    ],
)
def test_settings_file_write_is_single_flight_and_discards_a_stale_click(
    trigger_name: str,
    callback_name: str,
    generation_name: str,
    owner_name: str,
    current_check: str,
    invalidate_name: str,
    controls: tuple[str, ...],
) -> None:
    page = ast.unparse(_async_function("settings.py", "settings_page"))
    trigger = ast.unparse(_sync_function("settings.py", trigger_name))
    callback = _normalized_function_source("settings.py", callback_name)

    assert f"generation = {generation_name}[0]" in trigger
    assert f"if {owner_name}[0] is not None:" in trigger
    assert f"{owner_name}[0] = owner" in trigger
    assert f"{callback_name}(generation, owner" in trigger
    assert f"_run_owned({owner_name}, owner" in trigger
    for control in controls:
        assert control in page
    assert f"control.on_value_change({invalidate_name})" in page

    auth_index = callback.index("await require_live_session()")
    owner_index = callback.index(f"{current_check}(generation, owner)", auth_index)
    write_index = callback.index("write_dot_env(", owner_index)
    assert auth_index < owner_index < write_index


@pytest.mark.parametrize(
    (
        "save_trigger_name",
        "save_callback_name",
        "verify_trigger_name",
        "verify_callback_name",
        "generation_name",
        "owner_name",
        "current_check",
        "writeback",
    ),
    [
        (
            "trigger_save_ai_key",
            "save_ai_key_handler",
            "trigger_verify_connection",
            "verify_connection",
            "ai_key_generation",
            "ai_key_owner",
            "_ai_key_operation_is_current",
            "ai_key_input.value = masked",
        ),
        (
            "trigger_save_vision_key",
            "save_vision_key_handler",
            "trigger_verify_vision_connection",
            "verify_vision_connection",
            "vision_key_generation",
            "vision_key_owner",
            "_vision_key_operation_is_current",
            "vision_key_input.value = masked",
        ),
    ],
)
def test_settings_verify_and_save_share_one_current_operation_owner(
    save_trigger_name: str,
    save_callback_name: str,
    verify_trigger_name: str,
    verify_callback_name: str,
    generation_name: str,
    owner_name: str,
    current_check: str,
    writeback: str,
) -> None:
    page = _source("settings.py")
    save_trigger = ast.unparse(_sync_function("settings.py", save_trigger_name))
    verify_trigger = ast.unparse(_sync_function("settings.py", verify_trigger_name))
    save_callback = _normalized_function_source("settings.py", save_callback_name)
    verify_callback = _normalized_function_source(
        "settings.py",
        verify_callback_name,
    )

    for trigger, callback_name in (
        (save_trigger, save_callback_name),
        (verify_trigger, verify_callback_name),
    ):
        assert f"generation = {generation_name}[0]" in trigger
        assert f"if {owner_name}[0] is not None:" in trigger
        assert f"{owner_name}[0] = owner" in trigger
        assert f"{callback_name}(generation, owner" in trigger
        assert f"_run_owned({owner_name}, owner" in trigger
    assert f"on_click={verify_trigger_name}" in page

    save_index = save_callback.index("await save_ai_key(")
    save_owner_index = save_callback.index(
        f"{current_check}(generation, owner)",
        save_index,
    )
    save_writeback_index = save_callback.index(writeback, save_owner_index)
    assert save_index < save_owner_index < save_writeback_index

    verify_index = verify_callback.index("await verify_saved_ai_connection(")
    auth_index = verify_callback.index("await require_live_session()", verify_index)
    owner_index = verify_callback.index(
        f"{current_check}(generation, owner)",
        auth_index,
    )
    result_index = verify_callback.index("if result.code", owner_index)
    assert verify_index < auth_index < owner_index < result_index


def test_profile_display_name_save_is_single_flight_and_discards_a_stale_result() -> (
    None
):
    page = ast.unparse(_async_function("profile.py", "profile_page"))
    trigger = ast.unparse(_sync_function("profile.py", "trigger_save_display_name"))
    callback = _normalized_function_source("profile.py", "save_display_name")

    assert "generation = display_name_generation[0]" in trigger
    assert "new_name = display_name_input.value.strip()" in trigger
    assert "if display_name_owner[0] is not None:" in trigger
    assert "display_name_owner[0] = owner" in trigger
    assert "save_display_name(generation, owner, new_name)" in trigger
    assert "_run_owned(display_name_owner, owner" in trigger
    assert "display_name_input.on_value_change(_invalidate_display_name)" in page

    save_index = callback.index("await update_profile_display_name(")
    auth_index = callback.index("await require_live_session()", save_index)
    owner_index = callback.index(
        "_display_name_operation_is_current(generation, owner)",
        auth_index,
    )
    writeback_index = callback.index(
        "display_msg.set_text('✓ 显示名已保存')",
        owner_index,
    )
    assert save_index < auth_index < owner_index < writeback_index

    function = _async_function("profile.py", "save_display_name")
    handlers = [
        handler
        for node in ast.walk(function)
        if isinstance(node, ast.Try)
        for handler in node.handlers
    ]
    assert handlers
    for handler in handlers:
        assert "_display_name_operation_is_current(generation, owner)" in ast.unparse(
            handler
        )


@pytest.mark.parametrize(
    (
        "page",
        "trigger",
        "callback",
        "awaited_work",
        "writeback",
        "generation",
        "generation_guard",
    ),
    [
        (
            "settings.py",
            "trigger_save_ai_key",
            "save_ai_key_handler",
            "await save_ai_key(",
            "ai_key_input.value = masked",
            "ai_key_generation[0]",
            "_ai_key_operation_is_current(generation, owner)",
        ),
        (
            "settings.py",
            "trigger_save_vision_key",
            "save_vision_key_handler",
            "await save_ai_key(",
            "vision_key_input.value = masked",
            "vision_key_generation[0]",
            "_vision_key_operation_is_current(generation, owner)",
        ),
        (
            "profile.py",
            "trigger_save_password",
            "save_password",
            "await change_password(",
            "old_pwd_input.value = ''",
            "password_generation[0]",
            "password_generation[0]",
        ),
        (
            "prompt_mgmt.py",
            "trigger_save_version",
            "save_version",
            "await list_versions(",
            "history_container.clear()",
            "content_generation[0]",
            "content_generation[0]",
        ),
        (
            "prompt_mgmt.py",
            "trigger_test",
            "do_test",
            "await call_ai_text(",
            "test_result_out.value = text",
            "test_generation[0]",
            "test_generation[0]",
        ),
    ],
)
def test_sensitive_late_result_requires_click_generation_before_ui_writeback(
    page: str,
    trigger: str,
    callback: str,
    awaited_work: str,
    writeback: str,
    generation: str,
    generation_guard: str,
) -> None:
    trigger_source = ast.unparse(_sync_function(page, trigger))
    callback_source = _normalized_function_source(page, callback)

    assert generation in trigger_source
    work_index = callback_source.index(awaited_work)
    generation_index = callback_source.index(generation_guard, work_index)
    writeback_index = callback_source.index(writeback, work_index)
    assert work_index < generation_index < writeback_index


def test_prompt_rollback_collects_history_before_atomic_ui_writeback() -> None:
    source = _normalized_function_source("prompt_mgmt.py", "rollback")
    rollback_index = source.index("await rollback_to_version(")
    versions_index = source.index("await list_versions(", rollback_index)
    guard_index = source.index("content_generation[0]", versions_index)
    content_index = source.index("content_area.value =", versions_index)
    clear_index = source.index("container.clear()", versions_index)

    assert rollback_index < versions_index < guard_index < content_index < clear_index


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


def test_user_admin_table_query_is_frozen_by_a_synchronous_trigger() -> None:
    trigger = ast.unparse(_sync_function("user_admin.py", "trigger_reload_table"))
    query = _normalized_function_source("user_admin.py", "reload_table")

    for snapshot in (
        "state['page']",
        "page_size_select.value",
        "keyword_input.value.strip()",
        "role_filter.value",
        "table_generation[0] += 1",
    ):
        assert snapshot in trigger
    assert "await " not in trigger
    for mutable_control in (
        "page_size_select.value",
        "keyword_input.value",
        "role_filter.value",
    ):
        assert mutable_control not in query
    assert "on_click=lambda: trigger_reload_table(reset_page=True)" in _source(
        "user_admin.py"
    )


def test_user_admin_old_table_query_cannot_overwrite_a_newer_request() -> None:
    source = _normalized_function_source("user_admin.py", "reload_table")
    query_index = source.index("await list_users_for_admin(")
    auth_index = source.index("await _require_live_admin()", query_index)
    generation_index = source.index(
        "_table_query_is_current(query)",
        auth_index,
    )
    writeback_index = source.index("state['rows'] =", generation_index)

    assert query_index < auth_index < generation_index < writeback_index


def test_user_admin_pending_query_uses_a_separate_generation_before_render() -> None:
    trigger = ast.unparse(_sync_function("user_admin.py", "trigger_load_pending"))
    source = _normalized_function_source("user_admin.py", "load_pending")

    assert "pending_generation[0] += 1" in trigger
    assert "await " not in trigger
    query_index = source.index("await list_users_for_admin(")
    auth_index = source.index("await _require_live_admin()", query_index)
    generation_index = source.index(
        "_pending_query_is_current(generation)",
        auth_index,
    )
    clear_index = source.index("pending_container.clear()", generation_index)
    assert query_index < auth_index < generation_index < clear_index


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
    ("trigger", "callback", "snapshots", "operation"),
    [
        (
            "trigger_split",
            "_do_split",
            ("_capture_plan_target()", "raw_text_area.value", "state['grade']"),
            "async with AsyncSessionLocal()",
        ),
        (
            "trigger_generate_all",
            "_gen_all_daily",
            (
                "_capture_plan_target()",
                "goal_area.value",
                "adapted_area.value or original_area.value",
                "state['indoor_areas']",
                "state['outdoor_content']",
            ),
            "await is_near_holiday(",
        ),
        (
            "trigger_generate_reflection",
            "_gen_daily_reflection",
            (
                "_capture_plan_target()",
                "goal_area.value",
                "morning_activity_area.value",
                "outdoor_activity_area.value",
            ),
            "async with AsyncSessionLocal()",
        ),
        (
            "trigger_save",
            "_save_draft",
            (
                "_capture_plan_target()",
                "target.revision",
                "goal_area.value",
                "daily_reflection_area.value",
            ),
            "agent_panel.plan_changed(d)",
        ),
        (
            "trigger_export",
            "_export_word",
            ("_capture_plan_target",),
            "async with AsyncSessionLocal()",
        ),
    ],
)
def test_daily_plan_trigger_freezes_target_and_payload_before_async_auth(
    trigger: str,
    callback: str,
    snapshots: tuple[str, ...],
    operation: str,
) -> None:
    binding, capture = _bound_capture_source("daily_plan.py", trigger, callback)
    source = _normalized_function_source("daily_plan.py", callback)

    assert "await " not in capture
    for snapshot in snapshots:
        assert snapshot in capture
    assert f"on_click={trigger}" in _source("daily_plan.py")
    assert f"run={callback}" in binding

    auth_await = source.index("await _require_live_session()")
    target_guard = source.index("_is_current_plan_target(target)", auth_await)
    assert auth_await < target_guard < source.index(operation, target_guard)


def test_daily_plan_delete_freezes_target_before_opening_the_dialog() -> None:
    source = _normalized_function_source("daily_plan.py", "_delete_draft")
    auth_await = source.index("await _require_live_session()")
    for snapshot in (
        "target = _capture_plan_target()",
        "deleting_date = ",
        "deleting_plan_id = ",
        "deleting_revision = ",
    ):
        assert source.index(snapshot) < auth_await
    target_guard = source.index("_is_current_plan_target(target)", auth_await)
    assert auth_await < target_guard < source.index("with ui.dialog()", target_guard)


def test_daily_plan_batch_range_is_frozen_and_parsed_before_auth_await() -> None:
    binding, capture = _bound_capture_source(
        "daily_plan.py",
        "trigger_batch_export",
        "_batch_export",
    )
    for snapshot in (
        "batch_start_input.value",
        "batch_end_input.value",
        "start_date = datetime.strptime(",
        "end_date = datetime.strptime(",
    ):
        assert snapshot in capture
    assert "await " not in capture
    assert "run=_batch_export" in binding


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
    _binding, capture = _bound_capture_source(
        "daily_plan.py",
        "trigger_save",
        "_save_draft",
    )
    source = _normalized_function_source("daily_plan.py", "_save_draft")
    assert "_capture_plan_target()" in capture
    assert "goal_area.value" in capture
    payload_index = source.index("target, save_payload = frozen")
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


def test_daily_plan_target_tracks_every_editable_form_control_generation() -> None:
    source = _source("daily_plan.py")
    capture = ast.unparse(_sync_function("daily_plan.py", "_capture_plan_target"))
    current = ast.unparse(_sync_function("daily_plan.py", "_is_current_plan_target"))

    assert "form_generation=form_generation.capture()" in capture
    assert "form_generation=form_generation.capture()" in current
    for control in (
        "raw_text_area",
        "goal_area",
        "prep_area",
        "key_area",
        "difficult_area",
        "adapted_area",
        "morning_activity_area",
        "morning_talk_area",
        "area_game_area",
        "outdoor_activity_area",
        "daily_reflection_area",
    ):
        assert f"{control}.on_value_change(form_generation.advance)" in source


@pytest.mark.parametrize(
    ("callback", "awaited_work", "form_write"),
    [
        (
            "_do_split",
            "result = await process_lesson_plan(",
            "goal_area.value = result.activity_goal",
        ),
        (
            "_gen_all_daily",
            "results = await asyncio.gather(",
            "area.value = res",
        ),
        (
            "_gen_daily_reflection",
            "content = await generate_activity_content(",
            "daily_reflection_area.value = content",
        ),
        (
            "_load_draft",
            "plan = await get_daily_plan_by_date(",
            "goal_area.value = plan.activity_goal",
        ),
    ],
)
def test_daily_plan_programmatic_form_write_advances_generation(
    callback: str,
    awaited_work: str,
    form_write: str,
) -> None:
    _assert_guard_between(
        _normalized_function_source("daily_plan.py", callback),
        after=awaited_work,
        guard="form_generation.advance()",
        before=form_write,
    )


def test_daily_plan_batch_range_generation_guards_delayed_side_effects() -> None:
    page = _source("daily_plan.py")
    _binding, capture = _bound_capture_source(
        "daily_plan.py",
        "trigger_batch_export",
        "_batch_export",
    )
    source = _normalized_function_source("daily_plan.py", "_batch_export")

    assert "batch_start_input.on_value_change(batch_range_generation.advance)" in page
    assert "batch_end_input.on_value_change(batch_range_generation.advance)" in page
    assert "range_generation = batch_range_generation.capture()" in capture
    _assert_guard_between(
        source,
        after="await list_daily_plans_for_user(",
        guard="batch_range_generation.is_current(range_generation)",
        before="batch_msg.text =",
    )
    _assert_guard_between(
        source,
        after="doc_bytes = export_batch_daily_plans(",
        guard="batch_range_generation.is_current(range_generation)",
        before="file_path.write_bytes(doc_bytes)",
    )
    _assert_guard_between(
        source,
        after="doc_bytes = export_batch_daily_plans(",
        guard="batch_export_operations.owns(owner)",
        before="file_path.write_bytes(doc_bytes)",
    )
    _assert_guard_between(
        source,
        after="await save_export_record(",
        guard="batch_range_generation.is_current(range_generation)",
        before="ui.download(doc_bytes",
    )
    _assert_guard_between(
        source,
        after="await save_export_record(",
        guard="batch_export_operations.owns(owner)",
        before="ui.download(doc_bytes",
    )


def test_daily_plan_history_delete_revalidates_before_opening_dialog() -> None:
    source = _normalized_function_source("daily_plan.py", "_delete_plan")
    assert source.index("await _require_live_session()") < source.index(
        "with ui.dialog()"
    )


@pytest.mark.parametrize(
    ("callback", "owner"),
    [
        ("_do_split", "split_operations"),
        ("_gen_daily_reflection", "reflection_operations"),
        ("_save_draft", "save_operations"),
        ("_export_word", "export_operations"),
        ("_batch_export", "batch_export_operations"),
    ],
)
def test_daily_plan_finally_cleanup_requires_exact_operation_owner(
    callback: str,
    owner: str,
) -> None:
    function = _async_function("daily_plan.py", callback)
    finalizers = [
        ast.unparse(node)
        for node in ast.walk(function)
        if isinstance(node, ast.Try)
        and node.finalbody
        and "props(remove='loading')" in ast.unparse(node.finalbody)
    ]

    assert len(finalizers) == 1
    assert f"{owner}.owns(owner)" in finalizers[0]


def test_daily_plan_multi_generation_cleanup_requires_exact_operation_owner() -> None:
    source = _normalized_function_source("daily_plan.py", "_gen_all_daily")

    assert source.count("gen_all_btn.props(remove='loading')") == 3
    assert source.count("gen_all_operations.owns(owner)") == 3


def test_daily_plan_old_history_query_cannot_overwrite_newer_request() -> None:
    source = _normalized_function_source("daily_plan.py", "refresh_history")
    assert source.index(
        "request_generation = history_requests.advance()"
    ) < source.index("await _require_live_session()")
    _assert_guard_between(
        source,
        after="await list_daily_plans_for_user(",
        guard="history_requests.is_current(request_generation)",
        before="history_container.clear()",
    )
