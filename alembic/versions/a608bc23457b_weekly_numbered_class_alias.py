"""Match grade-qualified numbered legacy class labels in source guards."""

from pathlib import Path

import sqlalchemy as sa

from alembic import op, util

revision = "a608bc23457b"
down_revision = "f597ab12346a"
branch_labels = None
depends_on = None
_DIGITS = "一二三四五六七八九十百零〇两0-9"


def _key(name, grade, sqlite):
    if sqlite:
        return (
            f"(CASE WHEN {grade} IN ('小班','中班','大班') "
            f"AND substr({name},1,1)=substr({grade},1,1) "
            f"AND substr({name},-1)='班' AND length({name})>2 "
            f"AND substr({name},2,length({name})-2) NOT GLOB '*[^{_DIGITS}]*' "
            f"THEN substr({name},2) ELSE {name} END)"
        )
    return (
        f"(CASE WHEN {grade} IN ('小班','中班','大班') "
        f"AND REGEXP_LIKE({name},CONCAT('^',LEFT({grade},1),'[{_DIGITS}]+班$'),'c') "
        f"THEN SUBSTRING({name},2) ELSE {name} END)"
    )


def _prior():
    folder = str(Path(__file__).parent)
    owner = util.load_python_file(folder, "e486fa012359_owned_weekly_snapshots.py")
    morning = util.load_python_file(
        folder, "f597ab12346a_weekly_morning_activity_source.py"
    )
    return owner, morning


def upgrade():
    owner, morning = _prior()
    sqlite = morning._condition(owner.SQLITE_SOURCE)
    mysql = morning._condition(owner.MYSQL_SOURCE)
    sqlite = sqlite.replace(
        "d.class_name=c.display_name",
        _key("d.class_name", "d.grade", True)
        + "="
        + _key("c.display_name", "c.grade", True),
    )
    mysql = mysql.replace(
        "BINARY d.class_name=BINARY c.display_name",
        "BINARY "
        + _key("d.class_name", "d.grade", False)
        + "=BINARY "
        + _key("c.display_name", "c.grade", False),
    )
    owner._install(sqlite, mysql, owner.EVENT_GUARD)


def downgrade():
    if (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM shared_weekly_source s "
                "JOIN daily_plan d ON d.tenant_id=s.tenant_id AND d.id=s.source_id "
                "JOIN shared_weekly_version v ON v.tenant_id=s.tenant_id AND v.id=s.version_id "
                "JOIN shared_weekly_plan p ON p.tenant_id=v.tenant_id AND p.id=v.plan_id "
                "JOIN class_instance c ON c.tenant_id=p.tenant_id AND c.id=p.class_instance_id "
                "WHERE d.class_name<>c.display_name "
                "AND NOT EXISTS (SELECT 1 FROM daily_plan_identity m "
                "WHERE m.tenant_id=s.tenant_id AND m.daily_plan_id=s.source_id) LIMIT 1"
            )
        )
        .first()
    ):
        raise RuntimeError("class_alias_downgrade_requires_verified_restore")
    owner, morning = _prior()
    owner._install(
        morning._condition(owner.SQLITE_SOURCE),
        morning._condition(owner.MYSQL_SOURCE),
        owner.EVENT_GUARD,
    )
