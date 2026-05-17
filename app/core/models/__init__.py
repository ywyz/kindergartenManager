# 导入所有 model，确保 alembic autogenerate 能发现所有表
from app.core.models.user import User  # noqa: F401
from app.core.models.semester import SemesterConfig  # noqa: F401
from app.core.models.class_config import ClassConfig  # noqa: F401
from app.core.models.ai_key import AiApiKey  # noqa: F401

__all__ = ["User", "SemesterConfig", "ClassConfig", "AiApiKey"]
