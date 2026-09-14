"""Add the minimal WP-C authoritative identity subset.

Revision ID: 7c91e2a4b610
Revises: 6a8d2c4e9f10
"""

import sqlalchemy as sa

from alembic import op

revision = "7c91e2a4b610"
down_revision = "6a8d2c4e9f10"
branch_labels = None
depends_on = None


def _tables(metadata):
    def ident():
        return sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        )

    def tenant():
        return sa.Column("tenant_id", sa.BigInteger(), nullable=False)

    def col(name):
        return sa.Column(name, sa.BigInteger(), nullable=False)

    def dates(a, b):
        return [
            sa.Column(a, sa.Date(), nullable=False),
            sa.Column(b, sa.Date(), nullable=False),
            sa.CheckConstraint(f"{a} <= {b}", name=f"ck_{a}_{b}"),
        ]

    def stamps():
        return [
            sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.current_timestamp(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.current_timestamp(),
            ),
            sa.CheckConstraint("revision >= 1", name="ck_revision"),
        ]

    def fk(local, remote):
        return sa.ForeignKeyConstraint(local, remote, ondelete="RESTRICT")

    tables = []

    def table(name, *args):
        t = sa.Table(name, metadata, *args, mysql_engine="InnoDB")
        for constraint in t.constraints:
            if isinstance(constraint, sa.CheckConstraint) and constraint.name:
                constraint.name = f"{name}_{constraint.name}"
        for column in t.columns:
            if isinstance(column.type, sa.Integer) and (
                column.name == "tenant_id" or column.name.endswith("_id")
            ):
                t.append_constraint(
                    sa.CheckConstraint(
                        f"{column.name} > 0", name=f"ck_{name}_{column.name}_positive"
                    )
                )
        tables.append(t)
        return t

    table(
        "tenant_identity_guard",
        sa.Column("tenant_id", sa.BigInteger(), primary_key=True, autoincrement=False),
        *stamps(),
    )
    table(
        "tenant_identity_manager",
        tenant(),
        col("user_id"),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *stamps(),
        sa.PrimaryKeyConstraint("tenant_id", "user_id"),
        fk(["tenant_id", "user_id"], ["user.tenant_id", "user.id"]),
    )
    table(
        "academic_year",
        ident(),
        tenant(),
        sa.Column("label", sa.String(64), nullable=False),
        *dates("start_date", "end_date"),
        *stamps(),
        sa.UniqueConstraint("tenant_id", "id"),
    )
    table(
        "semester",
        ident(),
        tenant(),
        col("academic_year_id"),
        *dates("start_date", "end_date"),
        sa.Column("before_vacation_kind", sa.String(6), nullable=False),
        sa.Column("after_vacation_kind", sa.String(6), nullable=False),
        sa.CheckConstraint(
            "before_vacation_kind IN ('cold','summer') AND after_vacation_kind IN ('cold','summer')",
            name="ck_vacation",
        ),
        *stamps(),
        sa.UniqueConstraint("tenant_id", "id", "academic_year_id"),
        sa.UniqueConstraint("tenant_id", "id"),
        fk(
            ["tenant_id", "academic_year_id"],
            ["academic_year.tenant_id", "academic_year.id"],
        ),
    )
    table(
        "class_instance",
        ident(),
        tenant(),
        col("academic_year_id"),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("grade", sa.String(32), nullable=False),
        *stamps(),
        sa.UniqueConstraint("tenant_id", "id", "academic_year_id"),
        sa.UniqueConstraint("tenant_id", "id"),
        fk(
            ["tenant_id", "academic_year_id"],
            ["academic_year.tenant_id", "academic_year.id"],
        ),
    )
    table(
        "class_semester",
        tenant(),
        col("class_instance_id"),
        col("semester_id"),
        col("academic_year_id"),
        sa.Column(
            "membership_revision", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.CheckConstraint("membership_revision >= 1", name="ck_membership_revision"),
        *stamps(),
        sa.PrimaryKeyConstraint("tenant_id", "class_instance_id", "semester_id"),
        fk(
            ["tenant_id", "class_instance_id", "academic_year_id"],
            [
                "class_instance.tenant_id",
                "class_instance.id",
                "class_instance.academic_year_id",
            ],
        ),
        fk(
            ["tenant_id", "semester_id", "academic_year_id"],
            ["semester.tenant_id", "semester.id", "semester.academic_year_id"],
        ),
    )
    table(
        "teacher_class_assignment",
        ident(),
        tenant(),
        col("user_id"),
        col("class_instance_id"),
        col("semester_id"),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("valid_until", sa.DateTime(), nullable=False),
        sa.CheckConstraint("valid_from < valid_until", name="ck_validity"),
        *dates("scope_start_date", "scope_end_date"),
        sa.Column("revoked_at", sa.DateTime()),
        *stamps(),
        sa.UniqueConstraint("tenant_id", "id"),
        fk(["tenant_id", "user_id"], ["user.tenant_id", "user.id"]),
        fk(
            ["tenant_id", "class_instance_id", "semester_id"],
            [
                "class_semester.tenant_id",
                "class_semester.class_instance_id",
                "class_semester.semester_id",
            ],
        ),
    )
    table(
        "identity_audit",
        ident(),
        tenant(),
        col("actor_id"),
        col("target_id"),
        sa.Column("action", sa.String(32), nullable=False),
        sa.CheckConstraint("action = 'identity_manage'", name="ck_identity_action"),
        sa.Column("operation_kind", sa.String(32), nullable=False),
        sa.CheckConstraint(
            "operation_kind IN ('create_year','create_semester','create_class','bind_class','grant','revoke','manager_grant','manager_revoke')",
            name="ck_operation_kind",
        ),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.CheckConstraint("outcome = 'success'", name="ck_outcome"),
        sa.Column("reason", sa.String(16), nullable=False),
        sa.CheckConstraint("reason = 'authorized'", name="ck_reason"),
        sa.Column("operation_id", sa.String(36), nullable=False, unique=True),
        sa.Column("session_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
    )
    return tables


def upgrade():
    bind = op.get_bind()
    op.create_index("uq_user_tenant_id", "user", ["tenant_id", "id"], unique=True)
    metadata = sa.MetaData()
    sa.Table("user", metadata, autoload_with=bind)
    for table in _tables(metadata):
        table.create(bind)
    for event in ("UPDATE", "DELETE"):
        name = f"trg_identity_audit_no_{event.lower()}"
        if bind.dialect.name == "sqlite":
            op.execute(
                f"CREATE TRIGGER {name} BEFORE {event} ON identity_audit BEGIN SELECT RAISE(ABORT, 'identity_audit_immutable'); END"
            )
        else:
            op.execute(
                f"CREATE TRIGGER {name} BEFORE {event} ON identity_audit FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='identity_audit_immutable'"
            )


def downgrade():
    bind = op.get_bind()
    names = [
        "identity_audit",
        "teacher_class_assignment",
        "class_semester",
        "class_instance",
        "semester",
        "academic_year",
        "tenant_identity_manager",
        "tenant_identity_guard",
    ]
    for name in names:
        if bind.execute(sa.text(f"SELECT 1 FROM {name} LIMIT 1")).first():
            raise RuntimeError("identity_nonempty_downgrade_denied")
    for event in ("update", "delete"):
        op.execute(f"DROP TRIGGER trg_identity_audit_no_{event}")
    for name in names:
        op.drop_table(name)
    op.drop_index("uq_user_tenant_id", table_name="user")
