"""全局异常边界不能把异常正文或 traceback 写入日志。"""

from app import main as main_module


def test_global_exception_log_contains_only_safe_type(monkeypatch) -> None:
    captured: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def record(*args, **kwargs) -> None:
        captured.append((args, kwargs))

    monkeypatch.setattr(main_module.logger, "error", record)
    secret = "sk-unhandled-must-not-enter-log"
    endpoint = "https://private-provider.invalid/v1"

    main_module._on_global_exception(RuntimeError(f"{secret} {endpoint}"))

    assert len(captured) == 1
    rendered = repr(captured[0])
    assert "RuntimeError" in rendered
    assert secret not in rendered
    assert endpoint not in rendered
    assert "exc_info" not in captured[0][1]
