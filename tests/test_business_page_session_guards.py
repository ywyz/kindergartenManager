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


def _is_bound_guard(statement: ast.stmt) -> bool:
    if not isinstance(statement, ast.If) or not statement.body:
        return False
    test = statement.test
    if not isinstance(test, ast.UnaryOp) or not isinstance(test.op, ast.Not):
        return False
    operand = test.operand
    return (
        isinstance(operand, ast.Await)
        and isinstance(operand.value, ast.Call)
        and isinstance(operand.value.func, ast.Name)
        and operand.value.func.id == "_require_bound_session"
        and isinstance(statement.body[0], ast.Return)
    )


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
def test_external_effect_callbacks_fail_closed_before_any_other_work(
    relative_path: str,
) -> None:
    config = _PAGE_CALLBACKS[relative_path]
    functions = _async_functions(_parse(relative_path))

    assert config["callbacks"] <= functions.keys()
    for callback_name in config["callbacks"]:
        callback = functions[callback_name]
        assert _is_bound_guard(callback.body[0]), (
            f"{relative_path}:{callback.lineno} {callback_name} must begin with "
            "an exact-session guard"
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
