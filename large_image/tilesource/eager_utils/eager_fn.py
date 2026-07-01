"""Share eager iterator callables with worker processes."""

from collections.abc import Callable

_eager_fns: dict[str, Callable | None] = {
    'transform': None,
    'transform_scale': None,
}


def set_transform(fn: Callable) -> None:
    """Store the process-local eager transform callable.

    :param fn: A callable function with either one or three arguments that takes
        in a numpy array containing image data and returns a numpy array containing
        the transformed image data. If the function has three arguments, the first
        argument is the image data, the second argument is the x coordinate of the
        tile, and the third argument is the y coordinate of the tile as tile number
        (transform save mode: tile_x_y) or base pixel coordinates
        (transform save mode: region_x_y).
    :returns: None.
    """
    _eager_fns['transform'] = fn


def get_transform() -> Callable | None:
    """Return the process-local eager transform callable.

    :returns: The callable set by set_transform, or None if unset.
    """
    return _eager_fns['transform']


def set_transform_scale(fn: Callable) -> None:
    """Store the process-local eager transform-scale callable.

    :param fn: a callable function that takes in a numpy array of read_kwargs,
        a slide_dimensions dictionary, and returns a tuple containing the read coordinates,
        tile size, and target scale metadata in the following order: xlt, ytt,
        xrt, ybt, mm_x, mm_y, tile_size, target_scale, conv_mm_x, conv_mm_y.
        See default_region_coords_and_target_scale_from_read_args in
        eager_read_args.py for more details.
    :returns: None.
    """
    _eager_fns['transform_scale'] = fn


def get_transform_scale() -> Callable | None:
    """Return the process-local eager transform-scale callable.

    :returns: The callable set by set_transform_scale, or None if unset.
    """
    return _eager_fns['transform_scale']
