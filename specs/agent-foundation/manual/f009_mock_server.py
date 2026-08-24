"""Closed loopback mock for F009 browser acceptance.

Only a counter and closed synthetic scenario name are logged. Authorization,
system context, messages, business text, and tool arguments are never logged.
"""

from __future__ import annotations

import argparse
import copy
import hmac
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import sys
import threading
from uuid import UUID, uuid5

from f009_seed import (
    MOCK_API_KEY,
    MOCK_MODEL,
    MOCK_PORT,
    ManualHelperError,
    require_isolated_worktree,
)


_PATHS = (
    "activity_goal",
    "activity_prep",
    "activity_key",
    "activity_difficult",
    "activity_process_original",
    "activity_process_adapted",
    "morning_activity",
    "indoor_area",
    "outdoor_activity",
    "morning_talk_topic",
    "morning_talk_questions",
    "daily_reflection",
)
_WIRES = (
    "daily_plan__read_current",
    "daily_plan__read_context",
    "calendar__read_evaluation",
    "settings__read_class_areas",
    "daily_plan__draft_section_patch",
    "daily_plan__draft_reflection_patch",
)
_SCENARIOS = {
    "F009_TEXT": ("text", "F009_MOCK_TEXT_OK", False),
    "F009_DRAFT": ("draft", "F009_MOCK_DRAFT_READY", False),
    "F009_SLOW_CANCEL": ("slow_cancel", "F009_LATE_CANCEL_MARKER", True),
    "F009_SLOW_SCOPE": ("slow_scope", "F009_LATE_SCOPE_MARKER", True),
    "F009_SLOW_DISCONNECT": (
        "slow_disconnect",
        "F009_LATE_DISCONNECT_MARKER",
        True,
    ),
}
_CHAT = "/v1/chat/completions"
_DAY = re.compile(r"/holiday/info/\d{4}-\d{2}-\d{2}")
_YEAR = re.compile(r"/holiday/year/\d{4}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_MAX_BODY = 1_048_576


class MockRejected(ValueError):
    """Request is outside the frozen mock wire contract."""


def _schema(paths: tuple[str, ...] = ()) -> dict[str, object]:
    properties: dict[str, object] = {}
    required: list[str] = []
    if paths:
        required = [
            "base_fingerprint",
            "operation_id",
            "operations",
            "target",
            "turn_id",
        ]
        properties = {
            "operation_id": {"type": "string", "format": "uuid"},
            "turn_id": {"type": "string", "format": "uuid"},
            "target": {
                "type": "object",
                "properties": {
                    "daily_plan_id": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 2**63 - 1,
                    },
                    "plan_date": {"type": "string", "format": "date"},
                },
                "required": ["daily_plan_id", "plan_date"],
                "additionalProperties": False,
            },
            "base_fingerprint": {
                "type": "string",
                "pattern": "^[0-9a-f]{64}$",
            },
            "operations": {
                "type": "array",
                "minItems": 1,
                "maxItems": len(paths),
                "items": {
                    "type": "object",
                    "properties": {
                        "field_path": {"type": "string", "enum": sorted(paths)},
                        "before_value": {"type": "string", "maxLength": 4096},
                        "after_value": {"type": "string", "maxLength": 4096},
                    },
                    "required": ["field_path", "before_value", "after_value"],
                    "additionalProperties": False,
                },
            },
            "warnings": {
                "type": "array",
                "maxItems": 8,
                "items": {"type": "string", "minLength": 1, "maxLength": 256},
            },
        }
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": name,
            "parameters": _schema(
                tuple(path for path in _PATHS if path != "daily_reflection")
                if name == "daily_plan__draft_section_patch"
                else ("daily_reflection",)
                if name == "daily_plan__draft_reflection_patch"
                else ()
            ),
        },
    }
    for name in _WIRES
]


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(type(key) is str for key in value):
        raise MockRejected
    return value


def _uuid(value: object) -> str:
    if type(value) is not str:
        raise MockRejected
    try:
        if str(UUID(value)) != value:
            raise MockRejected
    except ValueError as exc:
        raise MockRejected from exc
    return value


def _system(message: dict[str, object]) -> dict[str, object]:
    if set(message) != {"role", "content"} or message.get("role") != "system":
        raise MockRejected
    content = message.get("content")
    if type(content) is not str:
        raise MockRejected
    try:
        value = _mapping(json.loads(content))
    except (json.JSONDecodeError, RecursionError) as exc:
        raise MockRejected from exc
    if (
        set(value)
        != {
            "base_fingerprint",
            "facts",
            "operation_id",
            "policy_version",
            "scope",
            "turn_id",
        }
        or value.get("policy_version") != "agent-foundation-v1"
    ):
        raise MockRejected
    operation_id, turn_id = (
        _uuid(value.get("operation_id")),
        _uuid(value.get("turn_id")),
    )
    fingerprint = value.get("base_fingerprint")
    if type(fingerprint) is not str or _SHA256.fullmatch(fingerprint) is None:
        raise MockRejected
    scope = _mapping(value.get("scope"))
    if set(scope) != {"daily_plan_id", "plan_date"}:
        raise MockRejected
    facts = value.get("facts")
    if not isinstance(facts, list) or len(facts) != 1:
        raise MockRejected
    plan = _mapping(facts[0])
    if set(plan) != {
        "class_name",
        "content_sha256",
        "grade",
        "plan_date",
        "plan_id",
        "sections",
        "updated_at_utc",
        "week_number",
        "weekday_cn",
    }:
        raise MockRejected
    plan_id, plan_date = plan.get("plan_id"), plan.get("plan_date")
    if (
        type(plan_id) is not int
        or plan_id <= 0
        or type(plan_date) is not str
        or scope != {"daily_plan_id": None, "plan_date": plan_date}
        or type(plan.get("content_sha256")) is not str
        or _SHA256.fullmatch(str(plan["content_sha256"])) is None
    ):
        raise MockRejected
    sections = plan.get("sections")
    if not isinstance(sections, list) or len(sections) != len(_PATHS):
        raise MockRejected
    parsed = [_mapping(section) for section in sections]
    if any(
        set(section) != {"content", "field_path", "truncated"} for section in parsed
    ):
        raise MockRejected
    by_path = {section.get("field_path"): section for section in parsed}
    if set(by_path) != set(_PATHS) or any(
        type(section.get("content")) is not str
        or type(section.get("truncated")) is not bool
        for section in parsed
    ):
        raise MockRejected
    return {
        "base_fingerprint": fingerprint,
        "before_value": by_path["activity_goal"]["content"],
        "operation_id": operation_id,
        "plan_date": plan_date,
        "plan_id": plan_id,
        "turn_id": turn_id,
    }


def _arguments(binding: dict[str, object]) -> dict[str, object]:
    return {
        "base_fingerprint": binding["base_fingerprint"],
        "operation_id": binding["operation_id"],
        "operations": [
            {
                "after_value": "F009 合成建议目标",
                "before_value": binding["before_value"],
                "field_path": "activity_goal",
            }
        ],
        "target": {
            "daily_plan_id": binding["plan_id"],
            "plan_date": binding["plan_date"],
        },
        "turn_id": binding["turn_id"],
        "warnings": ["F009 合成草案，仅供人工复核"],
    }


def _completed(content: str) -> dict[str, object]:
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "index": 0,
                "message": {"content": content, "role": "assistant"},
            }
        ]
    }


def _draft(binding: dict[str, object]) -> dict[str, object]:
    return {
        "choices": [
            {
                "finish_reason": "tool_calls",
                "index": 0,
                "message": {
                    "content": None,
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "function": {
                                "arguments": json.dumps(
                                    _arguments(binding),
                                    ensure_ascii=False,
                                    separators=(",", ":"),
                                    sort_keys=True,
                                ),
                                "name": "daily_plan__draft_section_patch",
                            },
                            "id": "f009-mock-draft-call",
                            "type": "function",
                        }
                    ],
                },
            }
        ]
    }


def _validate_draft_round(
    messages: list[dict[str, object]], binding: dict[str, object]
) -> None:
    if len(messages) != 4:
        raise MockRejected
    assistant, tool = messages[2], messages[3]
    if set(assistant) != {"role", "content", "tool_calls"} or assistant != {
        "role": "assistant",
        "content": None,
        "tool_calls": assistant.get("tool_calls"),
    }:
        raise MockRejected
    calls = assistant.get("tool_calls")
    if not isinstance(calls, list) or len(calls) != 1:
        raise MockRejected
    call = _mapping(calls[0])
    function = _mapping(call.get("function"))
    expected_id = str(uuid5(UUID(str(binding["operation_id"])), "f009-mock-draft-call"))
    if (
        set(call) != {"function", "id", "type"}
        or call.get("id") != expected_id
        or call.get("type") != "function"
        or set(function) != {"arguments", "name"}
        or function.get("name") != "daily_plan__draft_section_patch"
    ):
        raise MockRejected
    try:
        if json.loads(str(function.get("arguments"))) != _arguments(binding):
            raise MockRejected
    except (json.JSONDecodeError, RecursionError) as exc:
        raise MockRejected from exc
    if set(tool) != {"role", "tool_call_id", "content"} or tool.get("role") != "tool":
        raise MockRejected
    if tool.get("tool_call_id") != expected_id or type(tool.get("content")) is not str:
        raise MockRejected
    try:
        result = _mapping(json.loads(str(tool["content"])))
    except (json.JSONDecodeError, RecursionError) as exc:
        raise MockRejected from exc
    value = _mapping(result.get("value"))
    if (
        set(result) != {"error_code", "status", "value"}
        or result.get("status") != "ok"
        or result.get("error_code") is not None
        or set(value)
        != {
            "base_fingerprint",
            "canonical_sha256",
            "operation_id",
            "operations",
            "patch_id",
            "schema_version",
            "target",
            "tool_name",
            "turn_id",
            "warnings",
        }
        or value.get("operation_id") != binding["operation_id"]
        or value.get("turn_id") != binding["turn_id"]
        or value.get("base_fingerprint") != binding["base_fingerprint"]
        or value.get("tool_name") != "daily_plan.draft_section_patch"
        or value.get("target")
        != {"daily_plan_id": binding["plan_id"], "plan_date": binding["plan_date"]}
    ):
        raise MockRejected


def _prepare(
    payload: object, authorization: str, slow_seconds: float
) -> tuple[str, float, object]:
    if not hmac.compare_digest(authorization, f"Bearer {MOCK_API_KEY}"):
        raise MockRejected
    body = _mapping(payload)
    if set(body) != {"max_tokens", "messages", "model", "tool_choice", "tools"}:
        raise MockRejected
    if (
        body.get("model") != MOCK_MODEL
        or body.get("tool_choice") != "auto"
        or body.get("max_tokens") != 4096
    ):
        raise MockRejected
    if body.get("tools") != _TOOLS:
        raise MockRejected
    raw_messages = body.get("messages")
    if not isinstance(raw_messages, list) or len(raw_messages) not in {2, 4}:
        raise MockRejected
    messages = [_mapping(message) for message in raw_messages]
    binding = _system(messages[0])
    user = messages[1]
    if set(user) != {"role", "content"} or user.get("role") != "user":
        raise MockRejected
    intent = user.get("content")
    if type(intent) is not str:
        raise MockRejected
    selected = _SCENARIOS.get(intent)
    if selected is None:
        raise MockRejected
    scenario, content, slow = selected
    if len(messages) == 4:
        if scenario != "draft":
            raise MockRejected
        _validate_draft_round(messages, binding)
        return scenario, 0, _completed(content)
    response = _draft(binding) if scenario == "draft" else _completed(content)
    return scenario, slow_seconds if slow else 0, response


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, slow_seconds: float) -> None:
        super().__init__(("127.0.0.1", MOCK_PORT), _Handler)
        self.slow_seconds, self.counter = slow_seconds, 0
        self.counter_lock = threading.Lock()

    def next_number(self) -> int:
        with self.counter_lock:
            self.counter += 1
            return self.counter


class _Handler(BaseHTTPRequestHandler):
    server: _Server
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _send(self, status: HTTPStatus, value: object) -> None:
        body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
        try:
            self.send_response(status)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _reject(self, status: HTTPStatus = HTTPStatus.UNPROCESSABLE_ENTITY) -> None:
        self._send(status, {"error": {"code": "f009_mock_rejected"}})

    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        if _DAY.fullmatch(self.path):
            self._send(
                HTTPStatus.OK,
                {"holiday": None, "type": {"name": "synthetic", "type": 0}},
            )
        elif _YEAR.fullmatch(self.path):
            self._send(HTTPStatus.OK, {"code": 0, "holiday": {}})
        else:
            self._reject(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - stdlib API
        lengths = self.headers.get_all("Content-Length", [])
        auth = self.headers.get_all("Authorization", [])
        content_type = self.headers.get_all("Content-Type", [])
        if (
            self.path != _CHAT
            or len(lengths) != 1
            or len(auth) != 1
            or len(content_type) != 1
            or content_type[0].split(";", 1)[0].strip().lower() != "application/json"
        ):
            self._reject(HTTPStatus.BAD_REQUEST)
            return
        try:
            length = int(lengths[0])
            if not 0 < length <= _MAX_BODY:
                raise MockRejected
            payload = json.loads(
                self.rfile.read(length),
                parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
            )
            scenario, delay, response = _prepare(
                payload, auth[0], self.server.slow_seconds
            )
        except (ValueError, UnicodeError, RecursionError, MockRejected):
            self._reject()
            return
        number = self.server.next_number()
        print(
            json.dumps({"event": "accepted", "number": number, "scenario": scenario}),
            flush=True,
        )
        if delay:
            threading.Event().wait(delay)
        self._send(HTTPStatus.OK, response)


def _self_test() -> None:
    sections = [
        {"content": f"synthetic-{path}", "field_path": path, "truncated": False}
        for path in _PATHS
    ]
    system = {
        "base_fingerprint": "a" * 64,
        "facts": [
            {
                "class_name": "synthetic",
                "content_sha256": "b" * 64,
                "grade": "大班",
                "plan_date": "2026-09-07",
                "plan_id": 7,
                "sections": sections,
                "updated_at_utc": "2026-09-01T00:00:00+00:00",
                "week_number": 2,
                "weekday_cn": "周一",
            }
        ],
        "operation_id": "11111111-1111-1111-1111-111111111111",
        "policy_version": "agent-foundation-v1",
        "scope": {"daily_plan_id": None, "plan_date": "2026-09-07"},
        "turn_id": "22222222-2222-2222-2222-222222222222",
    }
    payload = {
        "max_tokens": 4096,
        "messages": [
            {"role": "system", "content": json.dumps(system)},
            {"role": "user", "content": "F009_DRAFT"},
        ],
        "model": MOCK_MODEL,
        "tool_choice": "auto",
        "tools": _TOOLS,
    }
    _prepare(payload, f"Bearer {MOCK_API_KEY}", 0.01)
    expanded = copy.deepcopy(payload)
    expanded["tools"][0]["function"]["parameters"]["properties"]["extra"] = {
        "type": "string"
    }
    try:
        _prepare(expanded, f"Bearer {MOCK_API_KEY}", 0.01)
    except MockRejected:
        print('{"self_test":"PASS"}')
        return
    raise ManualHelperError("expanded schema was accepted")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tested-sha")
    parser.add_argument("--slow-seconds", type=float, default=8.0)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            _self_test()
            return
        if args.tested_sha is None or not 0 < args.slow_seconds <= 30:
            raise ManualHelperError("tested SHA and delay 0..30 are required")
        require_isolated_worktree(
            args.tested_sha,
            secrets_absent=True,
            lock_absent=False,
        )
        server = _Server(args.slow_seconds)
        print('{"bind":"127.0.0.1:18081","event":"ready"}', flush=True)
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    except (ManualHelperError, OSError) as exc:
        print(f"F009 mock refused: {exc}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
