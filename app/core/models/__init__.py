# 导入所有 model，确保 alembic autogenerate 能发现所有表
from app.core.models.agent_write_evidence import (
    AgentWriteAudit,
    DailyPlanOperationVersion,
)
from app.core.models.ai_key import AiApiKey
from app.core.models.class_config import ClassConfig
from app.core.models.course_review_activity import CourseReviewActivity
from app.core.models.daily_plan import DailyPlan
from app.core.models.export_record import ExportRecord
from app.core.models.game_observation import GameObservation
from app.core.models.game_observation_image import GameObservationImage
from app.core.models.homemade_teaching import HomemadeTeachingToy
from app.core.models.indicator_catalog import IndicatorCatalog
from app.core.models.listening_domain import ListeningDomain
from app.core.models.listening_image import ListeningImage
from app.core.models.listening_indicator import ListeningIndicatorResult
from app.core.models.listening_record import ListeningRecord
from app.core.models.prompt_template import PromptTemplate
from app.core.models.semester import SemesterConfig
from app.core.models.user import User
from app.core.models.weekly_monthly_plan import (
    MonthlyThemeActivityItem,
    WeeklyActivityPlanDay,
    WeeklyMonthlyAuditEvent,
    WeeklyMonthlyPlan,
    WeeklyMonthlyPlanVersion,
    WeeklyMonthlyScopeGrant,
)

__all__ = [
    "AgentWriteAudit",
    "AiApiKey",
    "ClassConfig",
    "CourseReviewActivity",
    "DailyPlan",
    "DailyPlanOperationVersion",
    "ExportRecord",
    "GameObservation",
    "GameObservationImage",
    "HomemadeTeachingToy",
    "IndicatorCatalog",
    "ListeningDomain",
    "ListeningImage",
    "ListeningIndicatorResult",
    "ListeningRecord",
    "MonthlyThemeActivityItem",
    "PromptTemplate",
    "SemesterConfig",
    "User",
    "WeeklyActivityPlanDay",
    "WeeklyMonthlyAuditEvent",
    "WeeklyMonthlyPlan",
    "WeeklyMonthlyPlanVersion",
    "WeeklyMonthlyScopeGrant",
]

from app.core.models import (  # noqa: F401
    academic_identity,
    shared_weekly,
    source_mapping,
    weekly_people,
    weekly_sources,
)
