"""
Module for sharing a transform across eager iterator worker processes.
"""

from typing import Callable, Optional

_eager_iter_transform: Optional[Callable] = None


def set_transform(fn: Callable) -> None:
    global _eager_iter_transform
    _eager_iter_transform = fn


def get_transform() -> Optional[Callable]:
    return _eager_iter_transform