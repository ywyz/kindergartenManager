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
