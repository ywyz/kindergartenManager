from __future__ import annotations

import json
from uuid import uuid4


def test_get_logger_outputs_json(reload_step0_module, capsys) -> None:
    logging_module = reload_step0_module("app.core.logging", LOG_LEVEL="INFO")

    logger = logging_module.get_logger(f"step0-json-{uuid4().hex}")
    logger.info("hello")

    output = capsys.readouterr().out.strip()
    payload = json.loads(output)

    assert payload["message"] == "hello"
    assert payload["level"] == "INFO"
    assert payload["logger"] == logger.name
    assert "timestamp" in payload


def test_logger_respects_configured_level(reload_step0_module, capsys) -> None:
    logging_module = reload_step0_module("app.core.logging", LOG_LEVEL="INFO")

    logger = logging_module.get_logger(f"step0-level-{uuid4().hex}")
    logger.debug("hidden-debug")
    logger.info("visible-info")

    output_lines = [
        line for line in capsys.readouterr().out.splitlines() if line.strip()
    ]

    assert len(output_lines) == 1

    payload = json.loads(output_lines[0])
    assert payload["message"] == "visible-info"
    assert payload["level"] == "INFO"