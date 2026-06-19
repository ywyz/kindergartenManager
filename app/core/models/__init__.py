# 导入所有 model，确保 alembic autogenerate 能发现所有表
from app.core.models.user import User  # noqa: F401
from app.core.models.semester import SemesterConfig  # noqa: F401
from app.core.models.class_config import ClassConfig  # noqa: F401
from app.core.models.ai_key import AiApiKey  # noqa: F401
from app.core.models.daily_plan import DailyPlan  # noqa: F401
from app.core.models.prompt_template import PromptTemplate  # noqa: F401
from app.core.models.export_record import ExportRecord  # noqa: F401
from app.core.models.game_observation import GameObservation  # noqa: F401
from app.core.models.game_observation_image import GameObservationImage  # noqa: F401
from app.core.models.listening_record import ListeningRecord  # noqa: F401
from app.core.models.listening_domain import ListeningDomain  # noqa: F401
from app.core.models.listening_image import ListeningImage  # noqa: F401
from app.core.models.listening_indicator import ListeningIndicatorResult  # noqa: F401
from app.core.models.indicator_catalog import IndicatorCatalog  # noqa: F401

__all__ = [
    "User",
    "SemesterConfig",
    "ClassConfig",
    "AiApiKey",
    "DailyPlan",
    "PromptTemplate",
    "ExportRecord",
    "GameObservation",
    "GameObservationImage",
    "ListeningRecord",
    "ListeningDomain",
    "ListeningImage",
    "ListeningIndicatorResult",
    "IndicatorCatalog",
]
