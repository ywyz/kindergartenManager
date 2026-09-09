"""Independent daily activity title validation (not an Agent field)."""

ACTIVITY_NAME_MAX_BYTES = 256


def validate_activity_name(value: object, *, nullable: bool = True) -> None:
    """Reject coercion and truncation; preserve exact teacher text."""
    if value is None and nullable:
        return
    if type(value) is not str or len(value.encode("utf-8")) > ACTIVITY_NAME_MAX_BYTES:
        raise ValueError("activity_name must be text of at most 256 UTF-8 bytes")
