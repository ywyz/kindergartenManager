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
