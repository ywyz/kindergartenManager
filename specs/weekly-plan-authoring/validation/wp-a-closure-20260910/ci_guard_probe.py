"""Probe the existing test guard without importing application settings or running DDL."""

import ast
import hashlib
import json
from pathlib import Path

p = Path("specs/agent-foundation/tests/test_f009_zero_persistence_matrix_red.py")
s = p.read_text(encoding="utf-8")
tree = ast.parse(s)
wanted = {
    "FORBIDDEN_AGENT_SCHEMA_TERMS",
    "AUTHORIZED_AGENT_WRITE_EVIDENCE_TABLES",
    "AUTHORIZED_NON_AGENT_BUSINESS_TABLES",
}
nodes = [
    n
    for n in tree.body
    if isinstance(n, ast.Assign)
    and any(isinstance(t, ast.Name) and t.id in wanted for t in n.targets)
    or isinstance(n, ast.FunctionDef)
    and n.name == "_is_forbidden_agent_schema_name"
]
ns = {}
# Execute only the selected, reviewed local test constants/function; never user input.
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(p), "exec"), ns)  # noqa: S102
m = Path("alembic/versions/7c91e2a4b610_add_academic_identity.py")
mt = ast.parse(m.read_text(encoding="utf-8"))
names = {
    n.args[0].value
    for n in ast.walk(mt)
    if isinstance(n, ast.Call)
    and isinstance(n.func, ast.Name)
    and n.func.id == "table"
    and n.args
    and isinstance(n.args[0], ast.Constant)
    and isinstance(n.args[0].value, str)
}
allowed = (
    ns["AUTHORIZED_AGENT_WRITE_EVIDENCE_TABLES"]
    | ns["AUTHORIZED_NON_AGENT_BUSINESS_TABLES"]
)
failures = sorted(
    n for n in names - allowed if ns["_is_forbidden_agent_schema_name"](n)
)
print(
    json.dumps(
        {
            "test_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "existing_migration": m.as_posix(),
            "migration_table_names": sorted(names),
            "unexpected_forbidden_existing_business_tables": failures,
            "scope": "isolated test-name guard probe, not product business RED",
        },
        ensure_ascii=False,
    )
)
raise SystemExit(bool(failures))
