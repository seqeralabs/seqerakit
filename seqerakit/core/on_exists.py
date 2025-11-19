from enum import Enum, auto


class OnExists(Enum):
    """Enum defining behavior when a resource already exists."""

    FAIL = auto()
    IGNORE = auto()
    OVERWRITE = auto()
