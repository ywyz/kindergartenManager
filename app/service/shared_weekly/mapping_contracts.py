"""Identity-only previews; no teaching-body capability for managers."""

from dataclasses import dataclass
from datetime import date

from app.service.academic_identity.contracts import positive


@dataclass(frozen=True, slots=True)
class MappingTarget:
    daily_plan_id: int
    class_instance_id: int
    semester_id: int

    def __post_init__(self):
        for value in (self.daily_plan_id, self.class_instance_id, self.semester_id):
            positive(value)


@dataclass(frozen=True, slots=True)
class MappingStamp:
    id: int
    revision: int


@dataclass(frozen=True, slots=True)
class MappingPreview:
    candidate_id: str
    daily_plan_id: int
    creator_id: int
    source_date: date
    source_revision: int
    grade: str
    class_display: str
    class_instance_id: int
    semester_id: int
    previous: MappingStamp | None
