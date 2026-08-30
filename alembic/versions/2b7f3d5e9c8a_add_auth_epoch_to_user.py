"""add auth_epoch to user table

Revision ID: 2b7f3d5e9c8a
Revises: e5f7a9c2d4b6
Create Date: 2026-08-30 09:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2b7f3d5e9c8a"
down_revision: Union[str, Sequence[str], None] = "e5f7a9c2d4b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add auth_epoch column and preserve existing rows."""
    op.add_column(
        "user",
        sa.Column(
            "auth_epoch",
            sa.Integer(),
            sa.CheckConstraint(
                "auth_epoch >= 1",
                name="ck_user_auth_epoch_positive",
            ),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    user_table = sa.table(
        "user",
        sa.column("auth_epoch", sa.Integer()),
    )
    op.execute(
        user_table.update()
        .where(user_table.c.auth_epoch.is_(None))
        .values(auth_epoch=1)
    )


def downgrade() -> None:
    """Drop auth_epoch column while preserving legacy rows."""
    bind = op.get_bind()
    # SQLite keeps the CHECK inline with the column and removes both together.
    # MySQL promotes it to a named table constraint, which must be removed first.
    if bind.dialect.name != "sqlite":
        op.drop_constraint("ck_user_auth_epoch_positive", "user", type_="check")
    op.drop_column("user", "auth_epoch")
