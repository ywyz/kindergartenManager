"""业务页面必须把每个外部副作用绑定到打开页面时的登录 jti。"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


_ROOT = Path(__file__).parents[1]

_PAGE_CALLBACKS = {
    "app/ui/pages/course_review_activity.py": {
        "page": "course_review_activity_page",
        "callbacks": {
            "_save_current",
            "do_generate",
            "do_save",
            "do_export",
            "refresh_history",
            "_reexport",
            "_delete",
        },
        "double_check": {
            "do_generate",
            "do_export",
            "refresh_history",
            "_reexport",
            "_delete",
        },
    },
    "app/ui/pages/game_observation.py": {
        "page": "game_observation_page",
        "callbacks": {
            "handle_upload",
            "do_generate",
            "do_save",
            "do_export",
            "refresh_history",
            "_reexport",
            "_delete",
        },
        "double_check": {
            "handle_upload",
            "do_generate",
            "do_save",
            "do_export",
            "refresh_history",
            "_reexport",
            "_delete",
        },
    },
    "app/ui/pages/homemade_teaching.py": {
        "page": "homemade_teaching_page",
        "callbacks": {
            "_save_current",
            "do_generate",
            "do_save",
            "do_export",
            "refresh_history",
            "_reexport",
            "_delete",
        },
        "double_check": {
            "do_generate",
            "do_export",
            "refresh_history",
            "_reexport",
            "_delete",
        },
    },
    "app/ui/pages/one_on_one_listening.py": {
        "page": "one_on_one_listening_page",
        "callbacks": {
            "render_domains",
            "_on_upload",
            "_do_generate",
            "_pick_domain_workdays",
            "do_autopick_all",
            "_on_bulk_upload",
            "do_apply_bulk",
            "do_generate_all",
            "do_save",
            "do_export_combined",
            "do_export_split",
            "do_load_for_edit",
            "do_cancel_edit",
            "_show_detail",
            "_reexport_combined",
            "_reexport_split",
            "_delete_listening_record",
            "refresh_history",
            "do_batch_export",
        },
        "double_check": {
            "render_domains",
            "_on_upload",
            "_do_generate",
            "_pick_domain_workdays",
            "do_autopick_all",
            "_on_bulk_upload",
            "do_generate_all",
            "do_save",
            "do_export_combined",
            "do_export_split",
            "do_load_for_edit",
            "do_cancel_edit",
            "_show_detail",
            "_reexport_combined",
            "_reexport_split",
            "_delete_listening_record",
            "refresh_history",
            "do_batch_export",
        },
    },
}


def _parse(relative_path: str) -> ast.Module:
    return ast.parse((_ROOT / relative_path).read_text(encoding="utf-8"))


def _normalized_function_source(relative_path: str, name: str) -> str:
    functions = _async_functions(_parse(relative_path))
    return ast.unparse(functions[name])


def _assert_guard_between(source: str, *, after: str, before: str) -> None:
    after_index = source.index(after)
    guard_index = source.index(
        "await _require_bound_session()", after_index + len(after)
    )
    before_index = source.index(before, after_index + len(after))
    assert after_index < guard_index < before_index


def _async_functions(tree: ast.AST) -> dict[str, ast.AsyncFunctionDef]:
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef)
    }


def _sync_functions(tree: ast.AST) -> dict[str, ast.FunctionDef]:
    return {
        node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }


@pytest.mark.parametrize("relative_path", _PAGE_CALLBACKS)
def test_business_pages_use_shared_ui_operation_guard(relative_path: str) -> None:
    tree = _parse(relative_path)
    functions = _sync_functions(tree)

    assert "_claim_action" not in functions
    assert "_owns_action" not in functions
    assert not any(
        isinstance(node, ast.Name) and node.id == "action_owners"
        for node in ast.walk(tree)
    )
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "UiOperationGuard"
        for node in ast.walk(tree)
    )


def _is_bound_guard(statement: ast.stmt) -> bool:
    if not isinstance(statement, ast.If) or not statement.body:
        return False
    tests = (
        statement.test.values
        if isinstance(statement.test, (ast.BoolOp,))
        else [statement.test]
    )
    for test in tests:
        if not isinstance(test, ast.UnaryOp) or not isinstance(test.op, ast.Not):
            continue
        operand = test.operand
        if (
            isinstance(operand, ast.Await)
            and isinstance(operand.value, ast.Call)
            and isinstance(operand.value.func, ast.Name)
            and operand.value.func.id == "_require_bound_session"
        ):
            return isinstance(statement.body[0], ast.Return)
    return False


def _walk_body_without_nested_functions(function: ast.AsyncFunctionDef):
    stack: list[ast.AST] = list(reversed(function.body))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef, ast.Lambda)):
            continue
        stack.extend(reversed(list(ast.iter_child_nodes(node))))


def _bound_guard_count(function: ast.AsyncFunctionDef) -> int:
    return sum(
        1
        for node in _walk_body_without_nested_functions(function)
        if isinstance(node, ast.Await)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "_require_bound_session"
    )


@pytest.mark.parametrize("relative_path", _PAGE_CALLBACKS)
def test_page_entry_keeps_trusted_session_and_only_projects_for_shell(
    relative_path: str,
) -> None:
    config = _PAGE_CALLBACKS[relative_path]
    functions = _async_functions(_parse(relative_path))
    page = functions[config["page"]]

    first = page.body[0]
    assert isinstance(first, ast.Assign)
    assert isinstance(first.value, ast.Await)
    assert isinstance(first.value.value, ast.Call)
    assert isinstance(first.value.value.func, ast.Name)
    assert first.value.value.func.id == "require_current_ui_session"
    assert any(
        isinstance(target, ast.Name) and target.id == "ui_session"
        for target in first.targets
    )

    bound_calls = [
        node
        for node in ast.walk(page)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "require_bound_ui_session"
    ]
    assert bound_calls
    assert all(
        call.args
        and isinstance(call.args[0], ast.Name)
        and call.args[0].id == "ui_session"
        for call in bound_calls
    )

    shell_calls = [
        node
        for node in ast.walk(page)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "render_shell"
    ]
    assert len(shell_calls) == 1
    shell_actor = shell_calls[0].args[0]
    direct_projection = (
        isinstance(shell_actor, ast.Call)
        and isinstance(shell_actor.func, ast.Attribute)
        and shell_actor.func.attr == "as_user_dict"
    )
    if not direct_projection:
        assert isinstance(shell_actor, ast.Name) and shell_actor.id == "shell_user"
        shell_projection = [
            node
            for node in page.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "shell_user"
                for target in node.targets
            )
        ]
        assert len(shell_projection) == 1
        projection = shell_projection[0].value
        assert (
            isinstance(projection, ast.Call)
            and isinstance(projection.func, ast.Attribute)
            and isinstance(projection.func.value, ast.Name)
            and projection.func.value.id == "ui_session"
            and projection.func.attr == "as_user_dict"
        )


@pytest.mark.parametrize(
    ("relative_path", "query", "render"),
    [
        (
            "app/ui/pages/course_review_activity.py",
            "class_cfg = await get_class_config(",
            "context =",
        ),
        (
            "app/ui/pages/game_observation.py",
            "cls_cfg = await get_class_config(",
            "await render_shell(",
        ),
        (
            "app/ui/pages/homemade_teaching.py",
            "class_cfg = await get_class_config(",
            "context =",
        ),
        (
            "app/ui/pages/one_on_one_listening.py",
            "stages = await list_available_stages(",
            "stage_labels =",
        ),
    ],
)
def test_initial_actor_scoped_reads_revalidate_exact_jti_before_rendering(
    relative_path: str,
    query: str,
    render: str,
) -> None:
    config = _PAGE_CALLBACKS[relative_path]
    _assert_guard_between(
        _normalized_function_source(relative_path, config["page"]),
        after=query,
        before=render,
    )


@pytest.mark.parametrize("relative_path", _PAGE_CALLBACKS)
def test_external_effect_callbacks_have_no_await_before_exact_session_guard(
    relative_path: str,
) -> None:
    config = _PAGE_CALLBACKS[relative_path]
    functions = _async_functions(_parse(relative_path))

    assert config["callbacks"] <= functions.keys()
    for callback_name in config["callbacks"]:
        callback = functions[callback_name]
        source = ast.unparse(callback)
        assert source.index("await ") == source.index(
            "await _require_bound_session()"
        ), (
            f"{relative_path}:{callback.lineno} {callback_name} must authenticate "
            "before its first asynchronous boundary"
        )


@pytest.mark.parametrize("relative_path", _PAGE_CALLBACKS)
def test_long_or_confirmed_callbacks_revalidate_before_returning_data_or_writing(
    relative_path: str,
) -> None:
    config = _PAGE_CALLBACKS[relative_path]
    functions = _async_functions(_parse(relative_path))

    for callback_name in config["double_check"]:
        callback = functions[callback_name]
        assert _bound_guard_count(callback) >= 2, (
            f"{relative_path}:{callback.lineno} {callback_name} must revalidate "
            "after its await boundary"
        )


@pytest.mark.parametrize(
    ("relative_path", "trigger", "snapshots"),
    [
        (
            "app/ui/pages/course_review_activity.py",
            "trigger_generate",
            ("action_guard.capture_generation()", "_current_form_dict()"),
        ),
        (
            "app/ui/pages/course_review_activity.py",
            "trigger_save",
            ("action_guard.capture_generation()", "_current_form_dict()"),
        ),
        (
            "app/ui/pages/course_review_activity.py",
            "trigger_export",
            (
                "action_guard.capture_generation()",
                "_current_form_dict()",
                "state.get('record_id')",
            ),
        ),
        (
            "app/ui/pages/homemade_teaching.py",
            "trigger_generate",
            (
                "action_guard.capture_generation()",
                "dict(context)",
            ),
        ),
        (
            "app/ui/pages/homemade_teaching.py",
            "trigger_save",
            ("action_guard.capture_generation()", "_current_record_dict()"),
        ),
        (
            "app/ui/pages/homemade_teaching.py",
            "trigger_export",
            (
                "action_guard.capture_generation()",
                "_current_record_dict()",
                "state.get('record_id')",
            ),
        ),
        (
            "app/ui/pages/game_observation.py",
            "trigger_generate",
            (
                "state['generation']",
                "tuple(state['images'])",
                "_current_observation_payload()",
            ),
        ),
        (
            "app/ui/pages/game_observation.py",
            "trigger_save",
            (
                "state['generation']",
                "_current_observation_payload()",
                "tuple(state.get('compressed_images', []))",
            ),
        ),
        (
            "app/ui/pages/game_observation.py",
            "trigger_export",
            (
                "state['generation']",
                "_current_observation_payload()",
                "tuple(state.get('compressed_images', []))",
                "state.get('observation_id')",
            ),
        ),
    ],
)
def test_business_action_freezes_payload_and_generation_before_authentication(
    relative_path: str,
    trigger: str,
    snapshots: tuple[str, ...],
) -> None:
    source = ast.unparse(_sync_functions(_parse(relative_path))[trigger])

    for snapshot in snapshots:
        assert snapshot in source
    assert "await " not in source
    assert f'.on("click", {trigger})' in (_ROOT / relative_path).read_text(
        encoding="utf-8"
    )


def test_game_upload_captures_one_multiple_file_batch_synchronously() -> None:
    relative_path = "app/ui/pages/game_observation.py"
    source = ast.unparse(_sync_functions(_parse(relative_path))["trigger_upload"])

    assert "state['generation']" in source
    assert "state['upload_generation']" in source
    assert "len(state['images'])" in source
    assert "tuple(e.files)" in source
    assert "await " not in source
    page_source = (_ROOT / relative_path).read_text(encoding="utf-8")
    assert "on_multi_upload=trigger_upload" in page_source
    assert "on_upload=trigger_upload" not in page_source


def test_game_multiple_upload_keeps_siblings_but_discards_an_old_batch() -> None:
    source = _normalized_function_source(
        "app/ui/pages/game_observation.py",
        "handle_upload",
    )

    read_index = source.index("await file.read()")
    batch_guard_index = source.index(
        "upload_generation != state['upload_generation']",
        read_index,
    )
    form_guard_index = source.index(
        "generation != state['generation']",
        read_index,
    )
    extend_index = source.index("state['images'].extend(batch_data)")
    advance_index = source.index("state['generation'] += 1", extend_index)

    assert "for file in files:" in source
    assert "image_count + len(files) > 3" in source
    assert source.count("state['generation'] += 1") == 1
    assert read_index < batch_guard_index < extend_index < advance_index
    assert read_index < form_guard_index < extend_index


@pytest.mark.parametrize(
    ("trigger", "snapshots"),
    [
        ("trigger_render_domains", ("form_generation[0]", "stage_select.value")),
        ("trigger_upload", ("domain_states.get(d) is not s",)),
        (
            "trigger_generate",
            (
                "form_generation[0]",
                "tuple(s['raw_images'])",
                "child_name_input.value",
            ),
        ),
        (
            "trigger_pick_workdays",
            ("form_generation[0]", "s['year'].value", "s['month'].value"),
        ),
        ("trigger_autopick_all", ("form_generation[0]", "tuple(targets)")),
        ("trigger_bulk_upload", ("bulk_generation[0]",)),
        ("trigger_apply_bulk", ("form_generation[0]", "tuple(bulk_state['files'])")),
        ("trigger_generate_all", ("form_generation[0]", "tuple(targets)")),
        (
            "trigger_save",
            ("form_generation[0]", "_collect()", "edit_state.get('record_id')"),
        ),
        (
            "trigger_export_combined",
            ("form_generation[0]", "_collect()", "_export_record_dict()"),
        ),
        (
            "trigger_export_split",
            ("form_generation[0]", "_collect()", "_export_record_dict()"),
        ),
        ("trigger_load_for_edit", ("form_generation[0]", "rid")),
        (
            "trigger_batch_export",
            (
                "history_generation[0]",
                "tuple(sorted(selected_ids))",
                "filter_year.value",
                "filter_month.value",
            ),
        ),
    ],
)
def test_listening_actions_capture_targets_before_authentication(
    trigger: str,
    snapshots: tuple[str, ...],
) -> None:
    relative_path = "app/ui/pages/one_on_one_listening.py"
    source = ast.unparse(_sync_functions(_parse(relative_path))[trigger])

    for snapshot in snapshots:
        assert snapshot in source
    assert "await " not in source


def test_listening_renders_each_domain_section_once() -> None:
    source = _normalized_function_source(
        "app/ui/pages/one_on_one_listening.py",
        "render_domains",
    )
    assert source.count("_build_domain_section(") == 1


@pytest.mark.parametrize(
    ("callback", "awaited_work", "writeback", "generation_guard"),
    [
        (
            "render_domains",
            "await list_indicators(",
            "domains_container.clear()",
            "_form_is_current(generation)",
        ),
        (
            "_on_upload",
            "await e.file.read()",
            "s['raw_images'].append(",
            "domain_states.get(d) is not s",
        ),
        (
            "_do_generate",
            "await generate_domain_content(",
            "s['goals'].value =",
            "_form_is_current(generation)",
        ),
        (
            "_pick_domain_workdays",
            "await _auto_pick_workdays(",
            "date_input.value =",
            "_form_is_current(generation)",
        ),
        (
            "do_save",
            "await save_record_with_all(",
            "show_info(",
            "_form_is_current(generation)",
        ),
        (
            "do_export_combined",
            "await session.commit()",
            "ui.download(",
            "_form_is_current(generation)",
        ),
        (
            "do_export_split",
            "await session.commit()",
            "ui.download(",
            "_form_is_current(generation)",
        ),
        (
            "do_load_for_edit",
            "await load_record_detail(",
            "year_input.value =",
            "_form_is_current(generation)",
        ),
        (
            "refresh_history",
            "await list_records(",
            "history_container.clear()",
            "_history_is_current(generation)",
        ),
        (
            "do_batch_export",
            "await session.commit()",
            "ui.download(",
            "_history_is_current(generation)",
        ),
    ],
)
def test_listening_async_results_revalidate_session_and_target_before_writeback(
    callback: str,
    awaited_work: str,
    writeback: str,
    generation_guard: str,
) -> None:
    source = _normalized_function_source(
        "app/ui/pages/one_on_one_listening.py",
        callback,
    )
    work_index = source.index(awaited_work)
    session_index = source.index("await _require_bound_session()", work_index)
    target_index = source.index(generation_guard, work_index)
    writeback_index = source.index(writeback, work_index)
    assert work_index < session_index < writeback_index
    assert work_index < target_index < writeback_index


@pytest.mark.parametrize(
    "callback",
    [
        "do_load_for_edit",
        "_show_detail",
        "_reexport_combined",
        "_reexport_split",
    ],
)
def test_listening_record_reads_revalidate_before_not_found_ui(
    callback: str,
) -> None:
    source = _normalized_function_source(
        "app/ui/pages/one_on_one_listening.py",
        callback,
    )
    read_index = source.index("await load_record_detail(")
    session_index = source.index("await _require_bound_session()", read_index)
    not_found_index = source.index("if not detail:", read_index)
    assert read_index < session_index < not_found_index


def test_listening_delete_revalidates_after_committed_write() -> None:
    source = _normalized_function_source(
        "app/ui/pages/one_on_one_listening.py",
        "_delete_listening_record",
    )
    delete_index = source.index("await delete_record(")
    session_index = source.index("await _require_bound_session()", delete_index)
    target_index = source.index("_history_is_current(generation)", delete_index)
    success_index = source.index("show_info('已删除'", delete_index)
    assert delete_index < session_index < success_index
    assert delete_index < target_index < success_index


@pytest.mark.parametrize(
    ("callback", "awaited_work", "writeback"),
    [
        (
            "do_generate",
            "await generate_observation_content(",
            "goal_area.value =",
        ),
        (
            "do_save",
            "await save_observation_with_images(",
            "state['observation_id'] =",
        ),
        (
            "do_export",
            "await session.commit()",
            "ui.download(",
        ),
    ],
)
def test_game_result_revalidates_session_and_generation_before_writeback(
    callback: str,
    awaited_work: str,
    writeback: str,
) -> None:
    source = _normalized_function_source(
        "app/ui/pages/game_observation.py",
        callback,
    )
    _assert_guard_between(source, after=awaited_work, before=writeback)
    work_index = source.index(awaited_work)
    generation_index = source.index(
        "generation != state['generation']",
        work_index,
    )
    writeback_index = source.index(writeback, work_index)
    assert work_index < generation_index < writeback_index


@pytest.mark.parametrize(
    ("relative_path", "callback", "awaited_work", "writeback"),
    [
        (
            "app/ui/pages/course_review_activity.py",
            "do_generate",
            "await generate_course_review_activity_content(",
            "activity_goal_input.value =",
        ),
        (
            "app/ui/pages/course_review_activity.py",
            "do_export",
            "await session.commit()",
            "ui.download(",
        ),
        (
            "app/ui/pages/homemade_teaching.py",
            "do_generate",
            "await generate_homemade_teaching_content(",
            "toy_name_input.value =",
        ),
        (
            "app/ui/pages/homemade_teaching.py",
            "do_export",
            "await session.commit()",
            "ui.download(",
        ),
    ],
)
def test_business_result_revalidates_session_and_generation_before_writeback(
    relative_path: str,
    callback: str,
    awaited_work: str,
    writeback: str,
) -> None:
    source = _normalized_function_source(relative_path, callback)
    _assert_guard_between(source, after=awaited_work, before=writeback)
    work_index = source.index(awaited_work)
    generation_index = source.index("action_guard.is_current(generation)", work_index)
    writeback_index = source.index(writeback, work_index)
    assert work_index < generation_index < writeback_index


@pytest.mark.parametrize(
    ("relative_path", "generation_guard"),
    [
        (
            "app/ui/pages/course_review_activity.py",
            "action_guard.is_current(generation)",
        ),
        ("app/ui/pages/game_observation.py", "generation != state['generation']"),
        (
            "app/ui/pages/homemade_teaching.py",
            "action_guard.is_current(generation)",
        ),
    ],
)
@pytest.mark.parametrize("callback", ["do_generate", "do_save", "do_export"])
def test_business_async_error_paths_require_current_form_generation(
    relative_path: str,
    generation_guard: str,
    callback: str,
) -> None:
    function = _async_functions(_parse(relative_path))[callback]
    handlers = [
        handler
        for node in ast.walk(function)
        if isinstance(node, ast.Try)
        for handler in node.handlers
    ]
    assert handlers
    for handler in handlers:
        assert generation_guard in ast.unparse(handler)


@pytest.mark.parametrize(
    "relative_path",
    [
        "app/ui/pages/course_review_activity.py",
        "app/ui/pages/game_observation.py",
        "app/ui/pages/homemade_teaching.py",
    ],
)
@pytest.mark.parametrize("callback", ["do_generate", "do_save", "do_export"])
def test_business_terminal_cleanup_has_single_flight_owner(
    relative_path: str,
    callback: str,
) -> None:
    source = _normalized_function_source(relative_path, callback)
    assert "action_guard.owns(" in source[source.index("finally:") :]


@pytest.mark.parametrize(
    "relative_path",
    [
        "app/ui/pages/course_review_activity.py",
        "app/ui/pages/game_observation.py",
        "app/ui/pages/homemade_teaching.py",
    ],
)
def test_business_history_refresh_discards_older_query_results(
    relative_path: str,
) -> None:
    functions = _sync_functions(_parse(relative_path))
    trigger = ast.unparse(functions["trigger_refresh_history"])
    source = _normalized_function_source(relative_path, "refresh_history")

    assert "history_generation[0]" in trigger
    query_index = source.index("await list_")
    generation_index = source.index("_history_is_current(generation)", query_index)
    clear_index = source.index("history_container.clear()", query_index)
    assert query_index < generation_index < clear_index


@pytest.mark.parametrize("relative_path", _PAGE_CALLBACKS)
def test_async_failure_paths_revalidate_before_ui_writeback(
    relative_path: str,
) -> None:
    config = _PAGE_CALLBACKS[relative_path]
    functions = _async_functions(_parse(relative_path))
    violations: list[str] = []

    for callback_name in config["callbacks"]:
        callback = functions[callback_name]
        for node in ast.walk(callback):
            if not isinstance(node, ast.Try):
                continue
            body_has_await = any(
                isinstance(descendant, ast.Await)
                for statement in node.body
                for descendant in ast.walk(statement)
            )
            if not body_has_await:
                continue
            for handler in node.handlers:
                if not handler.body or not _is_bound_guard(handler.body[0]):
                    violations.append(f"{callback_name}:{handler.lineno}")

    assert not violations, (
        f"{relative_path} must revalidate before async failure writeback: "
        + ", ".join(violations)
    )


@pytest.mark.parametrize(
    ("relative_path", "getter"),
    [
        (
            "app/ui/pages/course_review_activity.py",
            "get_course_review_activity",
        ),
        (
            "app/ui/pages/homemade_teaching.py",
            "get_homemade_teaching_toy",
        ),
    ],
)
def test_reexport_detail_read_keeps_exact_actor_scope(
    relative_path: str,
    getter: str,
) -> None:
    callback = _async_functions(_parse(relative_path))["_reexport"]
    calls = [
        node
        for node in ast.walk(callback)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == getter
    ]

    assert len(calls) == 1
    assert {keyword.arg for keyword in calls[0].keywords} >= {
        "tenant_id",
        "user_id",
    }
