"""Eager iterator implementation for batched tile and region reads."""

import contextlib
import logging
import math
import multiprocessing
import os
import pickle
import random
import time
from collections import deque
from concurrent.futures import ALL_COMPLETED
from concurrent.futures import wait as wait_futures
from typing import Any, Callable, Dict, Optional, Union, cast

import numpy as np
from PIL import Image

from .. import tilesource
from .eager_utils import eager_fn
from .eager_utils.eager_image_modifications import pad_chunk_if_necessary, pad_tile, rgba2rgb
from .eager_utils.eager_pytorch_threading_context import _PyTorchThreadingContext
from .eager_utils.eager_read_args import (default_region_coords_and_target_scale_from_read_args,
                                          gen_read_args_for_regions,
                                          gen_read_args_for_tiles)
from .eager_utils.eager_shared_array import SharedArray
from .eager_utils.eager_wsi_operations import (calculate_slide_dimensions,
                                               return_relevant_tile_indexes_for_slide_dim,
                                               return_tile_slides_meeting_area_threshold)

_EAGER_FN_TRANSFORM_SENTINEL = '__large_image_eager_fn__'
_EAGER_FN_TRANSFORM_SCALE_SENTINEL = '__large_image_eager_fn_transform_scale__'


class EagerIterator:
    """Iterator that prefetches batched Large Image tile or region reads."""

    def __init__(
        self,
        source: 'tilesource.TileSource',
        output_mode: str = 'tiles',
        tile_overlap: Optional[Union[Dict[str, int] | Dict[str, float]]] = None,
        mask: Optional[Union[np.ndarray, str, os.PathLike]] = None,
        region: Optional[Dict[str, Any]] = None,
        scale: Optional[Dict[str, Any]] = None,
        tile_size: Optional[Dict[str, int]] = None,
        region_size: Optional[Dict[str, int]] = None,
        source_scale: Optional[Dict[str, Any]] = None,
        dtype: np.typing.DTypeLike = np.uint8,
        chunk_mult: int = 2,
        edge: bool = False,
        pad_mode: str = 'wsi_edge',
        pad_fill_mode: str = 'default',
        nchw: bool = False,
        batch: int = 64,
        prefetch: int = 16,
        workers: int = 16,
        tiles: Optional[Union[list, np.ndarray]] = None,
        regions: Optional[Union[list, np.ndarray]] = None,
        transform: Optional[Callable] = None,
        randomize_chunks: bool = False,
        seed: int = 42,
        area_threshold: float = 0.25,
        threshold_mask: float = 100,
        transform_save_mode: Optional[str] = 'tile_x_y',
        transform_scale: Optional[Callable] = None,
    ):
        """Initialize an eager iterator for batched tile or region reads.

        :param source: Tile source used to read image data.
        :param output_mode: Output mode, either 'tiles' or 'regions'.
        :param tile_overlap: Optional x and y tile overlap as pixels or fractions.
        :param mask: Optional whole-slide mask array or mask image path used to filter tiles.
        :param region: Optional source region with left, top, width, height, and units.
        :param scale: Optional target scale using magnification or mm_x and mm_y.
        :param tile_size: Optional output tile size with width and height in pixels.
        :param region_size: Optional output region size with width and height in pixels.
        :param source_scale: Source scale used when region units are mag_pixels.
        :param dtype: Numpy or torch dtype for the output image batch.
        :param chunk_mult: Chunk side length multiplier; chunk size is chunk_mult squared.
        :param edge: If True, discard reads that cross image boundaries.
        :param pad_mode: Padding mode used when reads are smaller than the requested output.
        :param pad_fill_mode: Fill mode used for padded pixels.
        :param nchw: If True, output batches use NCHW layout; otherwise NHWC layout.
        :param batch: Number of tiles or regions returned in each batch.
        :param prefetch: Number of batches to keep queued ahead of iteration.
        :param workers: Number of worker processes used for image reads.
        :param tiles: Optional tile indexes in row, column order for tile output mode.
        :param regions: Optional regions in top, left, height, width order for region mode.
        :param transform: Optional transform applied to each tile or region.
        :param randomize_chunks: If True, randomize chunk order before reading.
        :param seed: Random seed used when randomize_chunks is True.
        :param area_threshold: Minimum mask-signal fraction required for a tile.
        :param threshold_mask: Minimum mask pixel value considered signal.
        :param transform_save_mode: Coordinate mode passed to three-argument transforms.
        :param transform_scale: Optional callable that customizes read coordinates and scale.
        :returns: None. Iteration yields dictionaries containing image data and metadata.
        """
        logging.getLogger('tifftools').setLevel(logging.WARNING)
        self.source = source
        self._validate_init_args(
            output_mode, regions, scale, tile_size, tile_overlap, pad_mode, workers,
        )
        self._set_init_options(
            dtype, nchw, edge, batch, output_mode, scale, pad_fill_mode, pad_mode,
            chunk_mult, randomize_chunks, seed, tile_overlap, region, transform,
            transform_save_mode, transform_scale,
        )

        tiles, regions = self._setup_input_selection(
            output_mode, mask, region, scale, tile_size, region_size, source_scale,
            tiles, regions, area_threshold, threshold_mask,
        )
        self._cache_worker_dimension_args()
        self._worker_transform = self._prepare_worker_transform(self.transform)
        self._worker_transform_scale = self._prepare_worker_transform_scale(self.transform_scale)
        self._enable_dynamic_mm = self._worker_transform_scale is not None
        self.read_kwargs = self._build_read_kwargs(output_mode, tiles, regions, edge, chunk_mult)

        if randomize_chunks:
            random.seed(seed)
            random.shuffle(self.read_kwargs)

        self._configure_transform_scale(transform_scale)
        self._setup_out_dims()

        from concurrent.futures import ProcessPoolExecutor

        self.pool = ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context('fork'),
        )
        self._initialize(batch, prefetch)

    def _validate_init_args(
        self,
        output_mode: str,
        regions: Optional[Union[list, np.ndarray]],
        scale: Optional[Dict[str, Any]],
        tile_size: Optional[Dict[str, int]],
        tile_overlap: Optional[Union[Dict[str, int] | Dict[str, float]]],
        pad_mode: str,
        workers: int,
    ) -> None:
        """Validate constructor arguments that do not need source metadata.

        :param output_mode: Output mode, either 'tiles' or 'regions'.
        :param regions: Optional regions in top, left, height, width order.
        :param scale: Optional target scale using magnification or mm_x and mm_y.
        :param tile_size: Optional output tile size with width and height in pixels.
        :param tile_overlap: Optional x and y tile overlap as pixels or fractions.
        :param pad_mode: Padding mode used when reads are smaller than requested output.
        :param workers: Number of worker processes used for image reads.
        :returns: None.
        """
        self._validate_worker_count(workers)
        self._validate_output_mode(output_mode, regions, pad_mode)
        self._validate_scale(scale)
        self._validate_tile_size(tile_size)
        self._validate_tile_overlap(tile_overlap)

    @staticmethod
    def _validate_worker_count(workers: int) -> None:
        """Validate the worker count.

        :param workers: Number of worker processes used for image reads.
        :returns: None.
        """
        if workers <= 1:
            msg = 'Eager iterator requires at least 2 workers'
            raise ValueError(msg)

    @staticmethod
    def _validate_output_mode(
        output_mode: str, regions: Optional[Union[list, np.ndarray]], pad_mode: str,
    ) -> None:
        """Validate output-mode compatibility with related arguments.

        :param output_mode: Output mode, either 'tiles' or 'regions'.
        :param regions: Optional regions in top, left, height, width order.
        :param pad_mode: Padding mode used when reads are smaller than requested output.
        :returns: None.
        """
        if output_mode == 'regions' and not isinstance(regions, (list, np.ndarray)):
            msg = (
                "output_mode set to 'regions'.  Regions must be a numpy array "
                'of the form [[left, top, width, height], ...]'
            )
            raise ValueError(msg)
        if output_mode == 'tiles' and regions is not None:
            msg = "output_mode set to 'tiles' but regions provided"
            raise ValueError(msg)
        if output_mode == 'regions' and pad_mode == 'wsi_edge':
            msg = (
                'pad_mode cannot be wsi_edge if output_mode is regions. '
                "Please use pad_mode='equal' instead"
            )
            raise ValueError(msg)

    @staticmethod
    def _validate_scale(scale: Optional[Dict[str, Any]]) -> None:
        """Validate the requested target scale.

        :param scale: Optional target scale using magnification or mm_x and mm_y.
        :returns: None.
        """
        if scale is None:
            return
        has_mag = 'magnification' in scale
        has_mm_x = 'mm_x' in scale
        has_mm_y = 'mm_y' in scale
        if not has_mag and not (has_mm_x and has_mm_y):
            msg = "scale must be a dictionary with either 'magnification' or 'mm_x' and 'mm_y'"
            raise ValueError(msg)
        if has_mag and (has_mm_x or has_mm_y):
            msg = "scale cannot have both 'magnification' and 'mm_x' or 'mm_y'"
            raise ValueError(msg)
        if has_mm_x != has_mm_y:
            msg = "scale must have both 'mm_x' and 'mm_y'"
            raise ValueError(msg)

    @staticmethod
    def _validate_tile_size(tile_size: Optional[Dict[str, int]]) -> None:
        """Validate the requested output tile size.

        :param tile_size: Optional output tile size with width and height in pixels.
        :returns: None.
        """
        if tile_size is None:
            return
        if 'width' not in tile_size or 'height' not in tile_size:
            msg = "tile_size must be a dictionary with both 'width' and 'height'"
            raise ValueError(msg)
        if tile_size['width'] <= 0 or tile_size['height'] <= 0:
            msg = 'tile_size width and height must be greater than 0'
            raise ValueError(msg)

    @staticmethod
    def _validate_tile_overlap(
        tile_overlap: Optional[Union[Dict[str, int] | Dict[str, float]]],
    ) -> None:
        """Validate the requested tile overlap.

        :param tile_overlap: Optional x and y tile overlap as pixels or fractions.
        :returns: None.
        """
        if tile_overlap is None:
            return
        if 'x' not in tile_overlap or 'y' not in tile_overlap:
            msg = "tile_overlap must be a dictionary with both 'x' and 'y'"
            raise ValueError(msg)
        x_overlap = tile_overlap['x']
        y_overlap = tile_overlap['y']
        if type(x_overlap) is not type(y_overlap) or not isinstance(x_overlap, (int, float)):
            msg = 'tile_overlap x and y must be both integers or both floats'
            raise ValueError(msg)
        if x_overlap < 0 or y_overlap < 0:
            msg = 'tile_overlap x and y must be greater than or equal to 0'
            raise ValueError(msg)

    def _set_init_options(
        self,
        dtype: np.typing.DTypeLike,
        nchw: bool,
        edge: bool,
        batch: int,
        output_mode: str,
        scale: Optional[Dict[str, Any]],
        pad_fill_mode: str,
        pad_mode: str,
        chunk_mult: int,
        randomize_chunks: bool,
        seed: int,
        tile_overlap: Optional[Union[Dict[str, int] | Dict[str, float]]],
        region: Optional[Dict[str, Any]],
        transform: Optional[Callable],
        transform_save_mode: Optional[str],
        transform_scale: Optional[Callable],
    ) -> None:
        """Store constructor options on this iterator.

        :returns: None.
        """
        self.dtype: Any = dtype
        self.nchw = nchw
        self.edge = edge
        self.batch = batch
        self.output_mode = output_mode
        self.scale = scale
        self.pad_fill_mode = pad_fill_mode
        self.pad_mode = pad_mode
        self.chunk_mult = chunk_mult
        self.randomize_chunks = randomize_chunks
        self.seed = seed
        self.tile_overlap = tile_overlap
        self.region = region
        self.is_torch = False
        self.callable_arg_num = None
        self.transform = transform
        self.transform_save_mode = transform_save_mode
        self._worker_transform = None
        self._worker_transform_scale = None
        self.transform_scale: Optional[Callable] = transform_scale

    def _setup_input_selection(
        self,
        output_mode: str,
        mask: Optional[Union[np.ndarray, str, os.PathLike]],
        region: Optional[Dict[str, Any]],
        scale: Optional[Dict[str, Any]],
        tile_size: Optional[Dict[str, int]],
        region_size: Optional[Dict[str, int]],
        source_scale: Optional[Dict[str, Any]],
        tiles: Optional[Union[list, np.ndarray]],
        regions: Optional[Union[list, np.ndarray]],
        area_threshold: float,
        threshold_mask: float,
    ) -> tuple[Optional[Union[list, np.ndarray]], Optional[Union[list, np.ndarray]]]:
        """Prepare tile or region selection and slide dimensions.

        :returns: The normalized tiles and regions selections.
        """
        if output_mode == 'tiles':
            tiles = self._setup_tile_inputs(
                mask, region, scale, tile_size, source_scale, tiles, area_threshold, threshold_mask,
            )
            return tiles, regions
        if output_mode == 'regions' and regions is not None:
            regions = self._setup_region_inputs(regions, region, scale, region_size, source_scale)
            return tiles, regions
        msg = 'output mode must be either tiles or regions, If regions, regions must be provided'
        raise ValueError(msg)

    def _setup_tile_inputs(
        self,
        mask: Optional[Union[np.ndarray, str, os.PathLike]],
        region: Optional[Dict[str, Any]],
        scale: Optional[Dict[str, Any]],
        tile_size: Optional[Dict[str, int]],
        source_scale: Optional[Dict[str, Any]],
        tiles: Optional[Union[list, np.ndarray]],
        area_threshold: float,
        threshold_mask: float,
    ) -> Union[list, np.ndarray]:
        """Prepare tile-mode slide dimensions and tile indexes.

        :returns: Tile indexes in row, column order.
        """
        self.slide_dimensions = calculate_slide_dimensions(
            self.source, region, scale, tile_size, source_scale,
        )
        if tiles is None:
            tiles = return_relevant_tile_indexes_for_slide_dim(
                self.slide_dimensions, self.tile_overlap,
            )
        if mask is None:
            return tiles
        return self._filter_tiles_with_mask(mask, tiles, area_threshold, threshold_mask)

    def _filter_tiles_with_mask(
        self,
        mask: Optional[Union[np.ndarray, str, os.PathLike]],
        tiles: Union[list, np.ndarray],
        area_threshold: float,
        threshold_mask: float,
    ) -> Union[list, np.ndarray]:
        """Filter tile indexes by an optional mask.

        :returns: Tile indexes that pass the mask threshold, or the original tile indexes.
        """
        if isinstance(mask, str) and os.path.exists(mask):
            np.array(Image.open(mask))
            return tiles
        if isinstance(mask, np.ndarray):
            return return_tile_slides_meeting_area_threshold(
                mask, self.slide_dimensions, tiles, area_threshold=area_threshold,
                threshold_mask=threshold_mask,
            )
        msg = 'Mask must be a file path that exists or a numpy array'
        raise ValueError(msg)

    def _setup_region_inputs(
        self,
        regions: Union[list, np.ndarray],
        region: Optional[Dict[str, Any]],
        scale: Optional[Dict[str, Any]],
        region_size: Optional[Dict[str, int]],
        source_scale: Optional[Dict[str, Any]],
    ) -> np.ndarray:
        """Prepare region-mode slide dimensions and read regions.

        :returns: Regions as a numpy array.
        """
        regions_array = np.array(regions) if isinstance(regions, list) else regions
        if region_size is None:
            msg = 'region_size must be provided if output_mode is regions'
            raise ValueError(msg)
        if source_scale is not None:
            msg = 'source_scale parammter must be None for regions mode'
            raise ValueError(msg)
        if region is not None:
            msg = 'region parameter must be None for regions mode'
            raise ValueError(msg)
        self.slide_dimensions = calculate_slide_dimensions(
            self.source, region, scale, region_size, source_scale,
        )
        self._validate_region_size(regions_array)
        return regions_array

    def _validate_region_size(self, regions: np.ndarray) -> None:
        """Validate that region_size can contain all requested regions.

        :param regions: Regions in top, left, height, width order.
        :returns: None.
        """
        h_max = regions[:, 2].max()
        w_max = regions[:, 3].max()
        if (
            h_max <= self.slide_dimensions['tile_height_before_scaling'] and
            w_max <= self.slide_dimensions['tile_width_before_scaling']
        ):
            return
        msg = (
            'Desired region_size is smaller than needed for the regions provided\n'
            'Height, width max {}, {}\n'
            'Region height, width before scaling {}, {}'
        ).format(
            h_max,
            w_max,
            self.slide_dimensions['tile_height_before_scaling'],
            self.slide_dimensions['tile_width_before_scaling'],
        )
        raise ValueError(msg)

    def _cache_worker_dimension_args(self) -> None:
        """Cache stable scale and tile-size payloads for workers.

        :returns: None.
        """
        if self.slide_dimensions['scale_mode'] == 'mm':
            self.slide_dimensions['_target_scale'] = {
                'mm_x': self.slide_dimensions['target_mm_x'],
                'mm_y': self.slide_dimensions['target_mm_y'],
            }
        elif self.slide_dimensions['scale_mode'] == 'mag':
            self.slide_dimensions['_target_scale'] = {
                'magnification': self.slide_dimensions['target_magnification'],
            }
        else:
            msg = 'Invalid scale mode'
            raise ValueError(msg)
        self.slide_dimensions['_tile_size'] = dict(
            width=self.slide_dimensions['tile_size'][0],
            height=self.slide_dimensions['tile_size'][1],
        )

    def _build_read_kwargs(
        self,
        output_mode: str,
        tiles: Optional[Union[list, np.ndarray]],
        regions: Optional[Union[list, np.ndarray]],
        edge: bool,
        chunk_mult: int,
    ) -> list:
        """Build worker read argument chunks for the selected output mode.

        :returns: Read argument chunks for worker submission.
        """
        if output_mode == 'regions':
            assert isinstance(regions, (list, np.ndarray)), 'Regions must be a list or numpy array'
            return gen_read_args_for_regions(
                self.slide_dimensions, regions, edge=edge, chunk_mult=chunk_mult,
            )
        if output_mode == 'tiles':
            assert isinstance(tiles, (list, np.ndarray)), 'Tiles must be a list or numpy array'
            n_possible_tiles = (
                self.slide_dimensions['tile_target_range_x'] *
                self.slide_dimensions['tile_target_range_y']
            )
            return gen_read_args_for_tiles(
                n_possible_tiles, self.slide_dimensions, tiles, edge=edge,
                chunk_mult=chunk_mult, region=self.region,
            )
        msg = 'Supplied output mode must be either tiles or regions'
        raise ValueError(msg)

    def _configure_transform_scale(self, transform_scale: Optional[Callable]) -> None:
        """Validate and register a transform-scale callable.

        :param transform_scale: Optional callable that customizes read coordinates and scale.
        :returns: None.
        """
        if transform_scale is None:
            return
        transform_scale_result = self._call_transform_scale_probe(transform_scale)
        self._validate_transform_scale_result(transform_scale_result)
        eager_fn.set_transform_scale(transform_scale)

    def _call_transform_scale_probe(self, transform_scale: Callable) -> tuple:
        """Call transform_scale once to validate its signature and output.

        :param transform_scale: Callable that computes custom read coordinates and scale.
        :returns: The transform_scale probe result.
        """
        import inspect

        if len(inspect.signature(transform_scale).parameters) != 2:
            msg = (
                'transform_scale must have two parameters for read_kwargs, '
                'which is a list, and slide_dimensions'
            )
            raise ValueError(msg)
        try:
            return transform_scale(self.read_kwargs[0], self.slide_dimensions)
        except Exception as e:
            msg = 'Provided transform_scale test call failed.  Error: {}'.format(e)
            raise ValueError(msg) from e

    def _validate_transform_scale_result(self, transform_scale_result: tuple) -> None:
        """Validate transform-scale probe output.

        :param transform_scale_result: Result returned by a transform_scale probe call.
        :returns: None.
        """
        (
            xlt, ytt, xrt, ybt, mm_x, mm_y, tile_size_dict, target_scale, conv_mm_x, conv_mm_y,
        ) = transform_scale_result
        self.slide_dimensions['_tile_size'] = tile_size_dict
        if not self._has_valid_transform_scale_output(xlt, ytt, xrt, ybt, mm_x, mm_y, target_scale):
            msg = """
                transform_scale must return 9 values in the following order:
                xlt, ytt, xrt, ybt, mm_x, mm_y, target_scale, conv_mm_x, conv_mm_y = (
                    transform_scale(read_kwargs, slide_dimensions)
                )
                xlt: numpy array of left coordinates
                ytt: numpy array of top coordinates
                xrt: numpy array of right coordinates
                ybt: numpy array of bottom coordinates
                mm_x: numpy array of mm_x values
                mm_y: numpy array of mm_y values
                """
            raise ValueError(msg)
        self._validate_transform_scale_mode(target_scale)

    @staticmethod
    def _has_valid_transform_scale_output(
        xlt, ytt, xrt, ybt, mm_x, mm_y, target_scale,
    ) -> bool:
        """Return whether transform-scale outputs have expected types.

        :returns: True when coordinates are arrays and target_scale is a dictionary.
        """
        return (
            isinstance(xlt, np.ndarray) and
            isinstance(ytt, np.ndarray) and
            isinstance(xrt, np.ndarray) and
            isinstance(ybt, np.ndarray) and
            isinstance(mm_x, np.ndarray) and
            isinstance(mm_y, np.ndarray) and
            isinstance(target_scale, dict)
        )

    def _validate_transform_scale_mode(self, target_scale: Dict[str, Any]) -> None:
        """Validate transform-scale target scale for the active scale mode.

        :param target_scale: Target scale returned by transform_scale.
        :returns: None.
        """
        if self.slide_dimensions['scale_mode'] == 'mm' and 'mm_x' not in target_scale:
            msg = "transform_scale must return a dictionary with units 'mm' if scale_mode is 'mm'"
            raise ValueError(msg)
        if self.slide_dimensions['scale_mode'] == 'mm' and 'mm_y' not in target_scale:
            msg = "transform_scale must return a dictionary with units 'mm' if scale_mode is 'mm'"
            raise ValueError(msg)
        if self.slide_dimensions['scale_mode'] == 'mag' and 'magnification' not in target_scale:
            msg = (
                "transform_scale must return a dictionary with 'magnification' "
                "if scale_mode is 'mag'"
            )
            raise ValueError(msg)

    def _setup_out_dims(self):
        """Configure the output batch shape for untransformed reads.

        :returns: None.
        """
        self.out_dims = (
            self.batch,
            self.slide_dimensions['_tile_size']['height'],
            self.slide_dimensions['_tile_size']['width'],
            3,
        )

        if self.transform is not None:
            if self.transform_save_mode is not None and self.transform_save_mode not in [
                'tile_x_y',
                'region_x_y',
            ]:
                msg = "transform_save_mode must be either 'tile_x_y' or 'region_x_y'"
                raise ValueError(msg)
            self._setup_out_dims_for_transform()

        if self.nchw:
            self.out_dims = (self.out_dims[0], self.out_dims[3], self.out_dims[1], self.out_dims[2])

    def _prepare_worker_transform(self, transform: Optional[Callable]):
        """Register a transform callable for worker processes.

        :param transform: Transform callable or supported compose object.
        :returns: A worker-safe transform reference.
        """
        if transform is None:
            return None
        try:
            pickle.dumps(transform)
            return transform
        except Exception:
            from .eager_utils import eager_fn

            eager_fn.set_transform(transform)
            return _EAGER_FN_TRANSFORM_SENTINEL

    def _prepare_worker_transform_scale(self, transform_scale: Optional[Callable]):
        """Register a transform-scale callable for worker processes.

        :param transform_scale: Callable that computes custom read coordinates and scale.
        :returns: A worker-safe transform-scale reference.
        """
        if transform_scale is None:
            return None
        try:
            pickle.dumps(transform_scale)
            return transform_scale
        except Exception:
            from .eager_utils import eager_fn

            eager_fn.set_transform_scale(transform_scale)
            return _EAGER_FN_TRANSFORM_SCALE_SENTINEL

    def _setup_out_dims_for_transform(self):
        """Infer output shape and dtype after applying a transform.

        :returns: None.
        """
        test_data = np.zeros(self.out_dims[1:], dtype=self.dtype)
        transform = self.transform
        assert transform is not None
        if 'albumentations.core.composition.Compose' in str(type(transform)):
            test_out = transform(image=test_data)
            self.dtype = test_out['image'].dtype
            self.out_dims = tuple([self.out_dims[0]] + list(test_out['image'].shape))
            self.is_torch = False
        elif 'torchvision.transforms' in str(
            type(transform),
        ) or 'torchvision.transforms.v2' in str(type(transform)):
            test_out = transform(test_data)
            self.dtype = test_out.dtype
            self.out_dims = tuple([self.out_dims[0]] + list(test_out.shape))
            self.is_torch = True
        elif callable(transform):
            torch_module: Any
            try:
                import torch as torch_module
            except Exception:
                torch_module = None

            def _set_output_config(test_out):
                if isinstance(test_out, np.ndarray):
                    self.is_torch = False
                elif torch_module is not None and isinstance(test_out, torch_module.Tensor):
                    self.is_torch = True
                else:
                    msg = 'Transform callable must return a numpy array or torch.Tensor'
                    raise ValueError(msg)

                self.dtype = test_out.dtype
                self.out_dims = tuple([self.out_dims[0]] + list(test_out.shape))

            test_x = int(-1)
            test_y = int(-1)
            probe_errors = []

            for arg_num, args in ((1, (test_data,)), (3, (test_data, test_x, test_y))):
                try:
                    test_out = transform(*args)
                    _set_output_config(test_out)
                    self.callable_arg_num = arg_num
                    break
                except Exception as exc:
                    probe_errors.append(f'{arg_num}-arg probe failed: {exc}')
            else:
                msg = (
                    'Transform callable must accept either (image) or (image, x, y) '
                    'and return a numpy array or torch.Tensor. Errors: {}'.format(
                        '; '.join(probe_errors),
                    )
                )
                raise ValueError(
                    msg,
                )
        else:
            msg = (
                'Transform must be a albumentations.core.composition.Compose or '
                'torchvision.transforms.v2._container.Compose object or a callable'
            )
            raise ValueError(msg)

    def _initialize(self, batch: int, prefetch: int):
        """Initialize queue state and prefetch the first reads.

        :param batch: Number of tiles or regions returned in each batch.
        :param prefetch: Number of batches to keep queued ahead of iteration.
        :returns: None.
        """
        self.prefetch = prefetch
        self.batch = batch
        self.queue: deque[Any] = deque([])  # hold futures defining read operations
        self.overflow = 0  # count of tile overrun for latest batch
        self.pos = 0  # position in read_kwargs
        self._fill()

    def __iter__(self):
        """Return this iterator.

        :returns: The eager iterator instance.
        """
        return self

    def __enter__(self):
        """Enter a context manager for this iterator.

        :returns: The eager iterator instance.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit a context manager and clean up worker resources.

        :param exc_type: Exception type raised inside the context, if any.
        :param exc_val: Exception value raised inside the context, if any.
        :param exc_tb: Traceback raised inside the context, if any.
        :returns: None.
        """
        try:
            self.cleanup()
        except Exception as cleanup_exc:
            # Shared-memory cleanup can race across workers/processes; ignore
            # expected contention errors during teardown.
            is_shm_race = isinstance(cleanup_exc, (FileNotFoundError, BufferError)) or (
                isinstance(cleanup_exc, OSError) and 'No such file or directory' in str(cleanup_exc)
            )
            if not is_shm_race and exc_type is None:
                raise
        return False

    def cleanup(self, wait=True):
        """Shut down worker processes and release queued shared-memory buffers.

        :param wait: If True, wait for submitted worker tasks to finish before shutdown.
        :returns: None.
        """
        if hasattr(self, 'pool'):
            self.pool.shutdown(wait=wait, cancel_futures=True)
        # Clear any remaining shared arrays in the queue
        while self.queue:
            try:
                futures, tiles, batch_kwargs = self.queue.pop()
                # Wait for futures to complete before cleanup
                if futures:
                    wait_futures(futures, timeout=5, return_when=ALL_COMPLETED)
                try:
                    # Prefer explicit close to avoid BufferError on shutdown
                    if hasattr(tiles, 'close'):
                        tiles.close()
                finally:
                    del tiles
            except Exception:
                pass  # Ignore cleanup errors

    def __del__(self):
        """Clean up worker resources during object destruction.

        :returns: None.
        """
        # Use wait false to avoid waiting for submitted processes to execute
        # causing immediate exiting and returning to the main thread.
        with contextlib.suppress(Exception):
            self.cleanup(wait=False)

    def get_output_image_count(self):
        """Return the number of output images planned by this iterator.

        :returns: Number of tiles or regions available from the iterator.
        """
        count = 0
        for read_kwargs in self.read_kwargs:
            count += len(read_kwargs)
        return count

    def __next__(self):
        """Return the next eager batch.

        :returns: A dictionary containing a SharedArray under 'tile' and read metadata arrays.
        """
        # TODO: develop method for random batch retrieval
        if self.pos >= len(self.read_kwargs) and not len(self.queue):
            if self.randomize_chunks:
                random.shuffle(self.read_kwargs)
            raise StopIteration

        # wait on the futures linked to the next batch
        try:
            futures, tiles, batch_read_kwargs = self.queue.pop()
            if len(batch_read_kwargs.shape) == 1:
                batch_read_kwargs = np.expand_dims(batch_read_kwargs, axis=0)
            # Flatten futures if it's a list of lists (can happen when batches span multiple reads)
            # At line 720, futures can become a list of lists when batches > 1
            if futures and isinstance(futures[0], list):
                # futures is a list of lists, flatten it
                futures_flat = []
                for future_list in futures:
                    if isinstance(future_list, list):
                        futures_flat.extend(future_list)
                    else:
                        futures_flat.append(future_list)
            else:
                futures_flat = futures if isinstance(futures, list) else [futures]
            wait_futures(futures_flat, timeout=None, return_when=ALL_COMPLETED)
            # Check for exceptions in futures - this will raise if any future had an exception
            for future in futures_flat:
                future.result()  # This will raise any exception that occurred in the worker process
            self._fill()
        except Exception as e:
            # Add exception for read operation in multiprocessing pool to allow user to be aware
            # of potential issues with their callable transform
            self.pool.shutdown(wait=False, cancel_futures=True)
            msg = 'Exception in __next__: {}'.format(e)
            raise Exception(msg) from e

        # last batch may only have partial size
        if self.pos == len(self.read_kwargs) and not len(self.queue):
            # Use resize_shm to adjust the shape of the shared memory to prevent
            # issues if using pytorch tensors
            tiles.resize_shm([len(batch_read_kwargs), *tiles.shape[1:]])

        return self._tiles_and_read_kwargs_to_dict(tiles, batch_read_kwargs)

    def _tiles_and_read_kwargs_to_dict(self, tiles: SharedArray, read_kwargs: np.ndarray):
        """Convert batch tiles and read arguments into iterator output metadata.

        :param tiles: SharedArray containing the image batch.
        :param read_kwargs: Read argument rows used to produce the batch.
        :returns: A dictionary with tile data and metadata arrays for the batch.
        """
        # np_read_kwargs = np.array(read_kwargs)

        return {
            'format': 'numpy',
            'tile': tiles,
            'gx': read_kwargs[:, 6],  # left
            'gy': read_kwargs[:, 4],  # top
            'level_x': read_kwargs[:, 1],
            'level_y': read_kwargs[:, 0],
            'tile_position': {
                'level_x': read_kwargs[:, 1],
                'level_y': read_kwargs[:, 0],
                'region_x': read_kwargs[:, 3],
                'region_y': read_kwargs[:, 2],
            },
            'width': self.slide_dimensions['tile_size'][0],  # right - left
            'height': self.slide_dimensions['tile_size'][1],  # bottom - top
            'level': self.slide_dimensions['level'],
            'magnification': self.slide_dimensions['target_magnification'],
            'mm_x': self.slide_dimensions['target_mm_x'],
            'mm_y': self.slide_dimensions['target_mm_y'],
            'gwidth': self.slide_dimensions['tile_width_before_scaling'],
            'gheight': self.slide_dimensions['tile_height_before_scaling'],
        }

    @staticmethod
    def read(
        source: 'tilesource.TileSource',
        dtype: np.dtype,
        nchw: bool,
        read_kwargs: list,
        sharrs: list,
        offset: int,
        output_mode: str,
        batch: int,
        slide_dimensions: dict,
        region: Optional[Dict[str, Any]] = None,
        transform: Optional[Union[Callable, str]] = None,
        pad_mode: str = 'wsi_edge',
        pad_fill_mode: str = 'default',
        callable_arg_num: Optional[int] = None,
        transform_save_mode: Optional[str] = 'tile_x_y',
        worker_transform_scale: Optional[Union[Callable, str]] = None,
    ):
        """Read one eager chunk into shared-memory output buffers.

        :param source: Tile source used to read image data.
        :param dtype: Numpy or torch dtype for output images.
        :param nchw: If True, write transformed numpy tiles in NCHW layout.
        :param read_kwargs: Read argument rows for this worker task.
        :param sharrs: SharedArray buffers filled by this worker task.
        :param offset: Batch offset for the first output tile in this task.
        :param output_mode: Output mode, either 'tiles' or 'regions'.
        :param batch: Number of tiles or regions in each output batch.
        :param slide_dimensions: Slide dimension metadata from calculate_slide_dimensions.
        :param region: Optional source region used for tile clipping.
        :param transform: Optional transform applied to each tile or region.
        :param pad_mode: Padding mode used when reads are smaller than requested output.
        :param pad_fill_mode: Fill mode used for padded pixels.
        :param callable_arg_num: Number of positional arguments expected by transform.
        :param transform_save_mode: Coordinate mode passed to three-argument transforms.
        :param worker_transform_scale: Optional worker-safe transform-scale callable.
        :returns: None. The shared arrays are filled in place.
        """
        read_kwargs_array = np.asarray(read_kwargs)
        scale_data = EagerIterator._resolve_worker_scale_data(
            read_kwargs_array, slide_dimensions, worker_transform_scale,
        )
        xlt, ytt, xrt, ybt, mm_x, mm_y, tile_size_dict, target_scale, conv_mm_x, conv_mm_y = (
            scale_data
        )
        tile_y = read_kwargs_array[:, 2]
        tile_x = read_kwargs_array[:, 3]
        bounds = EagerIterator._read_bounds(xlt, ytt, xrt, ybt)
        EagerIterator._validate_worker_bounds(
            output_mode, bounds, slide_dimensions, read_kwargs_array,
        )
        xlo, yto, ho, wo = EagerIterator._output_slices(
            output_mode, xlt, ytt, xrt, ybt, bounds['xr'], bounds['yr'], conv_mm_x, conv_mm_y,
        )
        chunk = EagerIterator._read_chunk(source, slide_dimensions, target_scale, bounds)
        tiles = EagerIterator._extract_worker_tiles(
            output_mode, chunk, slide_dimensions, xlt, xrt, ytt, ybt, xlo, wo, yto, ho,
            tile_size_dict, region, pad_mode, pad_fill_mode,
        )
        tiles = EagerIterator._apply_worker_transform(
            tiles, transform, dtype, callable_arg_num, transform_save_mode,
            tile_x, tile_y, xlt, ytt,
        )
        EagerIterator._insert_worker_tiles(
            sharrs, tiles, offset, batch, nchw, worker_transform_scale, mm_x, mm_y,
        )

    @staticmethod
    def _resolve_worker_scale_data(
        read_kwargs: np.ndarray, slide_dimensions: dict, worker_transform_scale: Optional[Union[Callable, str]],
    ) -> tuple:
        """Resolve worker read coordinates and target scale.

        :param read_kwargs: Read argument rows for this worker task.
        :param slide_dimensions: Slide dimension metadata from calculate_slide_dimensions.
        :param worker_transform_scale: Optional worker-safe transform-scale callable.
        :returns: Coordinate arrays, scale metadata, tile size, and conversion factors.
        """
        if worker_transform_scale == _EAGER_FN_TRANSFORM_SCALE_SENTINEL:
            _worker_transform_scale = eager_fn.get_transform_scale()
            if _worker_transform_scale is None:
                msg = 'Eager transform-scale not set in eager_utils.eager_fn'
                raise ValueError(msg)
            return _worker_transform_scale(read_kwargs, slide_dimensions)
        if worker_transform_scale is not None:
            return cast(Callable, worker_transform_scale)(read_kwargs, slide_dimensions)
        return default_region_coords_and_target_scale_from_read_args(
            read_kwargs, slide_dimensions, include_mm=False,
        )

    @staticmethod
    def _read_bounds(xlt, ytt, xrt, ybt) -> Dict[str, Any]:
        """Return the source bounds needed for one worker chunk read.

        :returns: Bounds and maximum output dimensions for the chunk.
        """
        xr = np.min(xlt)
        yr = np.min(ytt)
        return {
            'xr': xr,
            'yr': yr,
            'w': np.max(xrt - xr),
            'h': np.max(ybt - yr),
            'ybmax': np.max(ybt - yr),
            'xrmax': np.max(xrt - xr),
        }

    @staticmethod
    def _validate_worker_bounds(
        output_mode: str, bounds: Dict[str, Any], slide_dimensions: dict, read_kwargs: np.ndarray,
    ) -> None:
        """Validate worker read bounds against the whole-slide image.

        :returns: None.
        """
        if bounds['xr'] < 0 or bounds['yr'] < 0:
            msg = (
                'Negative coordinates.\n Defaulting to 0.\n '
                'Please check your input tiles/regions.\n  Read_kwargs {}'
            ).format(read_kwargs)
            raise UserWarning(msg)
        if output_mode == 'regions' and (
            bounds['xrmax'] > slide_dimensions['base_size_x'] or
            bounds['ybmax'] > slide_dimensions['base_size_y']
        ):
            msg = (
                'Coordinates > image size.\n Defaulting to image boundaries.\n '
                'Please check your input tiles/regions. read_kwargs {}'
            ).format(read_kwargs)
            raise UserWarning(msg)

    @staticmethod
    def _output_slices(
        output_mode: str, xlt, ytt, xrt, ybt, xr, yr, conv_mm_x, conv_mm_y,
    ) -> tuple:
        """Return output slice coordinates for tiles or regions.

        :returns: Left, top, bottom, and right output slice arrays.
        """
        if output_mode not in {'tiles', 'regions'}:
            msg = 'Output mode not supported by read method.'
            raise ValueError(msg)
        xlo = np.floor(np.divide((xlt - xr), conv_mm_x)).astype(np.uint64)
        yto = np.floor(np.divide((ytt - yr), conv_mm_y)).astype(np.uint64)
        ho = yto + np.floor(np.divide((ybt - ytt), conv_mm_y)).astype(np.uint64)
        wo = xlo + np.floor(np.divide((xrt - xlt), conv_mm_x)).astype(np.uint64)
        return xlo, yto, ho, wo

    @staticmethod
    def _read_chunk(
        source: 'tilesource.TileSource', slide_dimensions: dict, target_scale: dict, bounds: dict,
    ) -> np.ndarray:
        """Read and normalize one worker chunk from the tile source.

        :returns: RGB numpy chunk data.
        """
        no_scale, kwargs = EagerIterator._chunk_read_kwargs(slide_dimensions, target_scale, bounds)
        if no_scale:
            chunk, _ = source.getRegion(**kwargs)
        else:
            chunk, _ = source.getRegionAtAnotherScale(**kwargs)
        assert isinstance(chunk, np.ndarray), 'Returned chunk must be a numpy array'
        return rgba2rgb(chunk)

    @staticmethod
    def _chunk_read_kwargs(
        slide_dimensions: dict, target_scale: dict, bounds: dict,
    ) -> tuple[bool, dict]:
        """Return source read kwargs and whether scaling can be skipped.

        :returns: A no-scale flag and keyword arguments for the source read.
        """
        source_region = dict(
            left=bounds['xr'].item(),
            top=bounds['yr'].item(),
            height=bounds['h'].item(),
            width=bounds['w'].item(),
            units='base_pixels',
        )
        if EagerIterator._is_no_scale_read(slide_dimensions, target_scale):
            return True, dict(region=source_region, format='numpy')
        return False, dict(sourceRegion=source_region, targetScale=target_scale, format='numpy')

    @staticmethod
    def _is_no_scale_read(slide_dimensions: dict, target_scale: dict) -> bool:
        """Return whether a worker chunk can be read without scale conversion.

        :returns: True when the requested target scale matches the base scale.
        """
        if slide_dimensions['scale_mode'] == 'mm':
            return (
                slide_dimensions['base_mm_x'] == target_scale['mm_x'] and
                slide_dimensions['base_mm_y'] == target_scale['mm_y']
            )
        if slide_dimensions['scale_mode'] == 'mag':
            return (
                slide_dimensions['base_magnification'] ==
                slide_dimensions['target_magnification']
            )
        msg = 'Invalid mode provided'
        raise ValueError(msg)

    @staticmethod
    def _extract_worker_tiles(
        output_mode: str,
        chunk: np.ndarray,
        slide_dimensions: dict,
        xlt,
        xrt,
        ytt,
        ybt,
        xlo,
        wo,
        yto,
        ho,
        tile_size_dict: dict,
        region: Optional[Dict[str, Any]],
        pad_mode: str,
        pad_fill_mode: str,
    ) -> list:
        """Extract individual tiles or regions from a worker chunk.

        :returns: List of extracted tile arrays.
        """
        if output_mode == 'tiles':
            return EagerIterator._extract_tile_mode_outputs(
                chunk, slide_dimensions, xlt, xrt, ytt, ybt, xlo, wo, yto, ho,
                tile_size_dict, region, pad_mode, pad_fill_mode,
            )
        if output_mode == 'regions':
            return EagerIterator._extract_region_mode_outputs(
                chunk, xlo, wo, yto, ho, tile_size_dict, pad_mode, pad_fill_mode,
            )
        msg = 'Output mode not supported by read method.'
        raise ValueError(msg)

    @staticmethod
    def _extract_tile_mode_outputs(
        chunk: np.ndarray,
        slide_dimensions: dict,
        xlt,
        xrt,
        ytt,
        ybt,
        xlo,
        wo,
        yto,
        ho,
        tile_size_dict: dict,
        region: Optional[Dict[str, Any]],
        pad_mode: str,
        pad_fill_mode: str,
    ) -> list:
        """Extract tile-mode outputs from a worker chunk.

        :returns: List of tile arrays.
        """
        h_max = np.max(ho).item()
        w_max = np.max(wo).item()
        chunk = pad_chunk_if_necessary(
            slide_dimensions, chunk, xlt, xrt, ytt, ybt, w_max, h_max, pad_mode, pad_fill_mode,
        )
        if region is None:
            return [
                chunk[yt:h, xl:w, :].astype(chunk.dtype)
                for (xl, w, yt, h) in zip(xlo, wo, yto, ho, strict=False)
            ]
        return [
            EagerIterator._pad_tile_if_needed(
                chunk[yt:h, xl:w, :].astype(chunk.dtype), h, w, tile_size_dict, pad_fill_mode,
            )
            for (xl, w, yt, h) in zip(xlo, wo, yto, ho, strict=False)
        ]

    @staticmethod
    def _pad_tile_if_needed(
        tile: np.ndarray, height: int, width: int, tile_size_dict: dict, pad_fill_mode: str,
    ):
        """Pad a tile when it is smaller than the requested output size.

        :returns: The original or padded tile array.
        """
        if height == tile_size_dict['height'] and width == tile_size_dict['width']:
            return tile
        return pad_tile(
            tile, tile_size_dict['width'], tile_size_dict['height'], 'right_bottom', pad_fill_mode,
        )

    @staticmethod
    def _extract_region_mode_outputs(
        chunk: np.ndarray,
        xlo,
        wo,
        yto,
        ho,
        tile_size_dict: dict,
        pad_mode: str,
        pad_fill_mode: str,
    ) -> list:
        """Extract region-mode outputs from a worker chunk.

        :returns: List of padded region arrays.
        """
        return [
            pad_tile(
                chunk[yt:h, xl:w, :].astype(chunk.dtype),
                tile_size_dict['width'],
                tile_size_dict['height'],
                pad_mode,
                pad_fill_mode,
            )
            for (xl, w, yt, h) in zip(xlo, wo, yto, ho, strict=False)
        ]

    @staticmethod
    def _apply_worker_transform(
        tiles: list,
        transform: Optional[Union[Callable, str]],
        dtype: np.dtype,
        callable_arg_num: Optional[int],
        transform_save_mode: Optional[str],
        tile_x,
        tile_y,
        xlt,
        ytt,
    ) -> list:
        """Apply an optional transform to worker tile outputs.

        :returns: Transformed tile outputs.
        """
        if not transform:
            return tiles
        transform = EagerIterator._resolve_worker_transform(transform)
        if 'albumentations.core.composition.Compose' in str(type(transform)):
            return [transform(image=tile)['image'].astype(dtype) for tile in tiles]
        if 'torchvision.transforms' in str(type(transform)):
            return [transform(tile) for tile in tiles]
        return EagerIterator._apply_callable_worker_transform(
            tiles, transform, dtype, callable_arg_num, transform_save_mode,
            tile_x, tile_y, xlt, ytt,
        )

    @staticmethod
    def _resolve_worker_transform(transform: Union[Callable, str]) -> Callable:
        """Resolve a sentinel transform into the process-local callable.

        :returns: Transform callable for this worker.
        """
        if transform != _EAGER_FN_TRANSFORM_SENTINEL:
            return cast(Callable, transform)
        resolved_transform = eager_fn.get_transform()
        if resolved_transform is None:
            msg = 'Eager transform not set in eager_utils.eager_fn'
            raise ValueError(msg)
        return resolved_transform

    @staticmethod
    def _apply_callable_worker_transform(
        tiles: list,
        transform: Callable,
        dtype: np.dtype,
        callable_arg_num: Optional[int],
        transform_save_mode: Optional[str],
        tile_x,
        tile_y,
        xlt,
        ytt,
    ) -> list:
        """Apply a user callable transform to worker tile outputs.

        :returns: Transformed tile outputs.
        """
        torch = EagerIterator._optional_torch_module()
        if callable_arg_num == 1:
            return [
                EagerIterator._cast_callable_output(transform(tile), dtype, torch) for tile in tiles
            ]
        if callable_arg_num == 3 and transform_save_mode == 'tile_x_y':
            return [
                EagerIterator._cast_callable_output(transform(tile, x, y), dtype, torch)
                for tile, x, y in zip(tiles, tile_x, tile_y, strict=False)
            ]
        if callable_arg_num == 3 and transform_save_mode == 'region_x_y':
            return [
                EagerIterator._cast_callable_output(transform(tile, x, y), dtype, torch)
                for tile, x, y in zip(tiles, xlt, ytt, strict=False)
            ]
        return tiles

    @staticmethod
    def _optional_torch_module():
        """Return torch if available for transform output checks.

        :returns: The torch module or None.
        """
        try:
            import torch
        except Exception:
            return None
        return torch

    @staticmethod
    def _cast_callable_output(tile_out, dtype: np.dtype, torch):
        """Cast a callable transform output to the requested dtype.

        :returns: A numpy array or torch tensor transform output.
        """
        if isinstance(tile_out, np.ndarray):
            return tile_out.astype(dtype)
        if torch is not None and isinstance(tile_out, torch.Tensor):
            return tile_out.to(dtype=dtype) if dtype is not None else tile_out
        msg = 'Transform callable must return a numpy array or torch.Tensor'
        raise ValueError(msg)

    @staticmethod
    def _insert_worker_tiles(
        sharrs: list,
        tiles: list,
        offset: int,
        batch: int,
        nchw: bool,
        worker_transform_scale: Optional[Union[Callable, str]],
        mm_x,
        mm_y,
    ) -> None:
        """Insert worker tile outputs into shared arrays.

        :returns: None.
        """
        for i, tile in enumerate(tiles):
            sharr_index, slice_index = divmod(offset + i, batch)
            if nchw and isinstance(tile, np.ndarray):
                sharrs[sharr_index].insert(np.transpose(tile, [2, 0, 1]), slice_index)
            else:
                sharrs[sharr_index].insert(tile, slice_index)
            if worker_transform_scale is not None:
                sharrs[sharr_index].insert_mm(mm_x[i], mm_y[i], slice_index)

    def _submitfn(self, read_kwargs: list, sharrs: list, offset: int):
        """Submit one eager read task to the process pool.

        :param read_kwargs: Read argument rows for the worker task.
        :param sharrs: SharedArray buffers filled by the worker task.
        :param offset: Batch offset for the first output tile in this task.
        :returns: A Future for the submitted worker task.
        """
        return self.pool.submit(
            EagerIterator.read,
            self.source,
            self.dtype,
            self.nchw,
            read_kwargs,
            sharrs,
            offset,
            self.output_mode,
            self.batch,
            self.slide_dimensions,
            self.region,
            self._worker_transform,
            self.pad_mode,
            self.pad_fill_mode,
            self.callable_arg_num,
            self.transform_save_mode,
            self._worker_transform_scale,
        )

    def _fill(self):
        """Fill the prefetch queue with eager read tasks.

        :returns: None.
        """

        def _fill_while():
            """Fill the queue with read operations for the process pool."""
            while len(self.queue) < self.prefetch and self.pos < len(self.read_kwargs):
                """if the last read from the prior batch spanned batch boundaries then
                the leftmost element in self.queue contains the futures, shared array,
                and read_kwargs to start the current batch
                """
                if self.overflow:
                    while len(self.queue) == 0:
                        time.sleep(0.01)
                    futures, tiles, batch_kwargs = self.queue.popleft()
                    if len(batch_kwargs.shape) == 1:
                        batch_kwargs = np.expand_dims(batch_kwargs, axis=0)
                else:
                    """last read aligned with batch boundary, create new shared array,
                    and read_kwargs, futures containers
                    """
                    tiles = SharedArray(
                        self.out_dims, self.dtype, self.is_torch, enable_mm=self._enable_dynamic_mm,
                    )
                    futures = []
                    # batch_kwargs = []
                    batch_kwargs = np.empty((0, self.read_kwargs[0].shape[1]))

                """submit enough jobs to fill at least one batch - a single job may
                fill multiple batches - or multiple jobs may be needed to fill one
                batch
                """
                offset = self.overflow
                batches = 1
                tiles = [tiles]
                while len(batch_kwargs) < self.batch and self.pos < len(
                    self.read_kwargs,
                ):
                    # number of batches spanned by this read
                    reads = self.read_kwargs[self.pos]
                    batches = math.ceil((len(reads) + offset) / self.batch)

                    # check if on last batch
                    # if (self.pos + 1) >= len(self.read_kwargs):
                    #     batch_dims = list(self.out_dims)
                    #     batch_dims[0] = len(batch_kwargs) + len(reads)
                    # else:
                    #     batch_dims = self.out_dims

                    # create additional arrays if this read spans multiple batches
                    sharrs = [
                        *tiles,
                        *[
                            SharedArray(
                                self.out_dims,
                                self.dtype,
                                self.is_torch,
                                enable_mm=self._enable_dynamic_mm,
                            )
                            for _ in range(batches - 1)
                        ],
                    ]

                    """submit job - read into first array in `tiles` at slice `offset`.
                    overflow to subsequent arrays if this read spans multiple batches.
                    if multiple reads are required to fill this batch then increment
                    the offset and submit another job on the next iteration
                    """
                    tiles = sharrs
                    futures.append(self._submitfn(reads, sharrs, offset))
                    offset = offset + len(reads)
                    batch_kwargs = np.concatenate([batch_kwargs, reads], axis=0)
                    self.pos = self.pos + 1
                self.overflow = len(batch_kwargs) % self.batch

                """ if last read spans multiple batches, link that read's future
                to the other batches - also divide kwargs according to batch boundaries
                """
                futures = [futures] + (batches - 1) * [[futures[-1]]]
                batch_kwargs_batches = [
                    batch_kwargs[i: i + self.batch]
                    for i in range(0, len(batch_kwargs), self.batch)
                ]

                # enqueue batches
                for f, t, b in zip(futures, tiles, batch_kwargs_batches, strict=False):
                    self.queue.appendleft((f, t, b))

        try:
            if self.is_torch:
                with _PyTorchThreadingContext():
                    _fill_while()
            else:
                _fill_while()

        except Exception as error:
            self.pool.shutdown(wait=False, cancel_futures=True)
            msg = 'Exception in _fill: {}'.format(error)
            raise Exception(msg) from error
