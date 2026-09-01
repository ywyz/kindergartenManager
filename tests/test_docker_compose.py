"""Deployment contracts for the supported Docker Compose topology."""

from pathlib import Path

import yaml


_ROOT = Path(__file__).parents[1]


def test_mysql_service_allows_app_owned_trigger_migrations() -> None:
    """The default app principal must be able to create Alembic triggers."""
    compose = yaml.safe_load((_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    command = compose["services"]["db"].get("command", ())

    if isinstance(command, str):
        arguments = command.split()
    else:
        arguments = list(command)

    assert "--log-bin-trust-function-creators=1" in arguments


def test_mysql_healthcheck_uses_the_configured_root_password() -> None:
    """Changing MYSQL_ROOT_PASSWORD must not make the database permanently unhealthy."""
    compose = yaml.safe_load((_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    healthcheck = compose["services"]["db"]["healthcheck"]["test"]
    rendered = " ".join(str(part) for part in healthcheck)

    assert "kg_root_2024" not in rendered
    assert "$${MYSQL_ROOT_PASSWORD}" in rendered


def test_compose_requires_explicit_database_passwords() -> None:
    """The supported server topology must not silently deploy known passwords."""
    compose = yaml.safe_load((_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    app_database_url = compose["services"]["app"]["environment"]["DATABASE_URL"]
    database_environment = compose["services"]["db"]["environment"]

    assert "kg_pass_2024" not in app_database_url
    assert "${MYSQL_PASSWORD:?" in app_database_url
    assert "${MYSQL_ROOT_PASSWORD:?" in database_environment["MYSQL_ROOT_PASSWORD"]
    assert "${MYSQL_PASSWORD:?" in database_environment["MYSQL_PASSWORD"]


def test_app_service_does_not_receive_mysql_root_credentials() -> None:
    """The least-privileged app container must never inherit DB root credentials."""
    compose = yaml.safe_load((_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    application = compose["services"]["app"]
    database_environment = compose["services"]["db"]["environment"]

    assert "MYSQL_ROOT_PASSWORD" in database_environment
    assert "env_file" not in application
    assert "MYSQL_ROOT_PASSWORD" not in application["environment"]
    assert "BOOTSTRAP_ADMIN_ALLOW_REMOTE" not in application["environment"]


def test_app_healthcheck_uses_python_stdlib_readiness_probe() -> None:
    compose = yaml.safe_load((_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    healthcheck = compose["services"]["app"]["healthcheck"]
    rendered = " ".join(str(part) for part in healthcheck["test"])

    assert "python" in rendered
    assert "urllib.request" in rendered
    assert "http://127.0.0.1:8080/api/v1/readiness" in rendered
    assert "curl" not in rendered


def test_caddy_waits_for_the_application_to_be_ready() -> None:
    compose = yaml.safe_load((_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))

    assert compose["services"]["caddy"]["depends_on"]["app"] == {
        "condition": "service_healthy"
    }
    assert compose["services"]["app"]["depends_on"]["db"] == {
        "condition": "service_healthy"
    }


def test_production_caddy_requires_a_domain_and_explicit_tls() -> None:
    """The default topology must fail closed instead of serving an HTTP-only :80 site."""
    compose = yaml.safe_load((_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    caddy_environment = compose["services"]["caddy"].get("environment", {})
    caddyfile = (_ROOT / "Caddyfile").read_text(encoding="utf-8")
    active_lines = [
        line.strip()
        for line in caddyfile.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert "${CADDY_DOMAIN:?" in str(caddy_environment.get("CADDY_DOMAIN", ""))
    assert any(line.startswith("https://{$CADDY_DOMAIN}") for line in active_lines)
    assert ":80" not in active_lines
