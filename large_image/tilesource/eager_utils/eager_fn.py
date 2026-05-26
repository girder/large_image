"""Share eager iterator callables with worker processes."""

from typing import Callable, Optional

_eager_iter_transform: Optional[Callable] = None
_eager_iter_transform_scale: Optional[Callable] = None


def set_transform(fn: Callable) -> None:
    """Store the process-local eager transform callable.

    :param fn: Callable to apply to eager tiles in worker processes.
    :returns: None.
    """
    global _eager_iter_transform
    _eager_iter_transform = fn


def get_transform() -> Optional[Callable]:
    """Return the process-local eager transform callable.

    :returns: The callable set by set_transform, or None if unset.
    """
    return _eager_iter_transform


def set_transform_scale(fn: Callable) -> None:
    """Store the process-local eager transform-scale callable.

    :param fn: Callable that computes read coordinates and target scale metadata.
    :returns: None.
    """
    global _eager_iter_transform_scale
    _eager_iter_transform_scale = fn


def get_transform_scale() -> Optional[Callable]:
    """Return the process-local eager transform-scale callable.

    :returns: The callable set by set_transform_scale, or None if unset.
    """
    return _eager_iter_transform_scale
