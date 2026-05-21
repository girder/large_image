"""
Module for sharing a transform across eager iterator worker processes.
"""
import sys
from typing import Callable, Optional

_eager_iter_transform: Optional[Callable] = None
_eager_iter_transform_scale: Optional[Callable] = None


def set_transform(fn: Callable) -> None:
    sys.modules[__name__]._eager_iter_transform = fn


def get_transform() -> Optional[Callable]:
    return getattr(sys.modules[__name__], '_eager_iter_transform', None)


def set_transform_scale(fn: Callable) -> None:
    sys.modules[__name__]._eager_iter_transform_scale = fn


def get_transform_scale() -> Optional[Callable]:
    return getattr(sys.modules[__name__], '_eager_iter_transform_scale', None)
