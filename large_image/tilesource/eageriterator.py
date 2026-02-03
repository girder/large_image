import math, os, random, time, pickle
from typing import Optional, Tuple, Union, Callable, Dict, Any
import logging
from collections import deque

from .eager_utils.eager_image_modifications import pad_tile, pad_chunk_if_necessary, rgba2rgb
from .eager_utils import eager_fn
from .eager_utils.eager_shared_array import SharedArray
from .eager_utils.eager_pytorch_threading_context import _PyTorchThreadingContext

import multiprocessing
from concurrent.futures import ALL_COMPLETED, wait

import numpy as np
from PIL import Image

from .. import tilesource

_EAGER_FN_SENTINEL = "__large_image_eager_fn__"

class EagerIterator:
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
            source_scale: Optional[Union[int, float]] = None,
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
            threshold_mask: Union[int, float] = 100,
            transform_save_mode: Optional[str] = 'tile_x_y'
            ):
        """
        Initialize the EagerIterator class.  The EagerIterator class is an iterator intended for use in AI/ML applications.
        The eager iterator uses large_image source object which creates this iterator to read tiles or regions. The iterator
        provides numpy arrays of the requested tiles or regions.  The goal of this iterator is to simplify operations such
        as tiling and region extraction at specific resolutions/scales.  The format of output batches will always be numpy.     
        

        :param source: the tile source to use. this object should be provided a large_image tile source and will be provided
            by the large image library if you use the tile source's eagerIterator method.
        :param output_mode: A string corresponding to the output mode of the iterator. Can be either 'tiles' or 'regions'.  Defaults to 'tiles'.
        :param tile_overlap: A float or integer defining the tile_overlap in percentage between tiles.  If float, must be in range of 0 and 1.  Cannot be 1.  
            If integer, must be in range of 0 and the smallest dimension of the tile size.  Defaults to 0.
        :param mask: An optional numpy array or path to a 1 channel image that will be used to filter the tiles (only useful in tile mode).  This mask image is interpreted 
            based on two additional optional parameters: area_threshold and threshold_mask.  area_threshold is used to determine if a patch acquired from the mask
            contains enough signal to be used for a tile to be included in the output.  threshold_mask is used to determine if a pixel value within the mask corresponds to 
            signal.  If the mask is a uint8 array with values 0 to 1, then area_threshold will effectively be 1 instead of the default 100.  If the mask is a boolean array,
            then any True value will be considered signal.  Defaults to None.
        :param scale: An optional dictionary defining the scale produced for the iterator. If scale can be configured for both magnification and mm.
            If 'magnification' is defined in dictionary then it will be in magnification scaling mode.  If 'mm_x' and 'mm_y' then it will use a mm/px scaling mode.  Defaults to None.
        :param tile_size: An optional dictionary specifying the desired width and height in pixels of the output tiles.  If provided, width and height must be provided as integers If None, will use the default tile size of the slide.  Defaults to None.
        :param region_size: An optional tuple of integers (x, y) defining the desired size in pixels of output regions. If None, will use the default region size of the slide.  Defaults to None.
        :param dtype: An optional numpy data type for the output image batch. Defaults to np.uint8.
        :param chunk_mult: An integer shaping the number regions/tiles to be grouped in a single read. Defaults to 2.  
            Chunk size is this number squared. i.e. chunk_multi of 2 = chunk_size of 2^2.
        :param edge: A boolean controlling whether to include (False) or discard (True) tiles with incomplete regions at the image boundaries. Defaults to False.
        :param pad_mode: A string defining the padding mode to be used.  Can be either 'equal' or 'wsi_edge'.  Defaults to 'wsi_edge'.
        :param pad_fill_mode: A string defining the padding fill mode to be used.  Can be either 'default', 'max', integer for value in all RGB channels, 
            or tuple of int with respective values in RGB channels (R, G, B).  Defaults to 'default'.
        :param nchw: A boolean controlling whether to return the output in NCHW format (True) or NHWC format (False). Defaults to False.  
            Will transpose transformed output as well.
        :param batch: An integer for number of regions/tiles to be retrieved in a single batch. Defaults to 64.
        :param prefetch: An integer for number of batches to be prefetched. Defaults to 16.
        :param workers: An integer for number of worker processes to use. Defaults to 16.
        :param tiles: A list of tiles in the form [[y/column, x/row], ...] to be used in output_mode 'tiles'.  Defaults to None.
        :param regions: A numpy array in the shape of [n, 4]  where top = [:,0], left = [:,1], height = [:,2], width = [:,3]. Only used in output_mode 'regions'.  
            Defaults to None.
        :param transform: An optional callable.  If provided an albumentations compose object it will apply the transform as the image keywordargument.  If provided a 
            torchvision.transforms.v2._container it will apply the transform as a callable.  For albumentations or torchvision v2 transforms, this must be a compose object rather 
            than a callable.  Torchvision v2 transforms requires a limiting number of threads to 1 during the read operation.
            Otherwise, will apply the transform by calling the transform with the tile as a positional argument. Defaults to None.
        :param randomize_chunks: A boolean controlling whether to randomize order of the chunks to make the output batches more random. Defaults to False.
        :param seed: A seed for the random number generator that will be used for randomizing the chunks. Defaults to 42.
        :param area_threshold: A float defining the area threshold for the mask to be used to filter the tiles.  It is a value between 0 and 1 defining the portion 
            of the tile that must be signal defined in the mask to be included in the output.  Defaults to 0.25.
        :param threshold_mask: An integer defining the pixel value threshold for for a pixel to contribute to signal as defined in the mask.  Defaults to 100.

        :returns: An iterator that returns a dictionary with keys defined below. The image key is 'tile' which returns a SharedArray of the images.  The SharedArray can be accessed for use by using .view() (for example, batch['tile'].view())  
            Keys that are not-consistent between tiles (such as tile, gx, gy, level_x, level_y, etc.) will return a numpy array of values
              with values specific for tiles or regions returned in a batch.  The dictionary has the following keys:
            'format': 'numpy',
            'gx': left,
            'gy': top,
            'level_x': level_x,
            'level_y': level_y,
            'tile': tile images in the form of a SharedArray,
            'tile_position': {'level_x': level_x, 'level_y': level_y, 'region_x': region_x, 'region_y': region_y},
            'width': width,
            'height': height,
            'level': level,
            'magnification': magnification,
            'mm_x': mm_x,
            'mm_y': mm_y,
            'gwidth': gwidth,
            'gheight': gheight
        
        Given its specific use case, the eager iterator does not support all of the options available in the tileIterator.  
        The eager iterator does not support the following options:
            - region
            - format

        This iterator is experimental and may not work with all tile sources.  Please consider the different expected inputs when attempting to use the eager iterator.
        """
        # Import eager_utils here to avoid attempting to load pykdtree when not needed
        from .eager_utils.eager_read_args import gen_read_args_for_tiles, gen_read_args_for_regions
        from .eager_utils.eager_wsi_operations import calculate_slide_dimensions, return_relevant_tile_indexes_for_slide_dim, return_tile_slides_meeting_area_threshold

        logging.getLogger("tifftools").setLevel(logging.WARNING)
    
        # Tile source becomes the source for the iterator allowing its options to be used
        self.source = source

        if workers <= 1:
            raise ValueError("Eager iterator requires at least 2 workers")

        # Check for valid output mode
        if output_mode == 'regions' and not (isinstance(regions, list) or isinstance(regions, np.ndarray)):
            raise ValueError("output_mode set to 'regions'.  Regions must be a numpy array of the form  [[left, top, width, height], ...]")
        elif output_mode == 'tiles' and regions is not None:
            raise ValueError("output_mode set to 'tiles' but regions provided")

        if output_mode == 'regions' and pad_mode == 'wsi_edge':
            raise ValueError("pad_mode cannot be wsi_edge if output_mode is regions.  Please use pad_mode='equal' instead")
        
        if scale is not None:
            if 'magnification' not in scale and ('mm_x' not in scale and 'mm_y' not in scale):
                raise ValueError("scale must be a dictionary with either 'magnification' or 'mm_x' and 'mm_y'")
            elif 'magnification' in scale and ('mm_x' in scale or 'mm_y' in scale):
                raise ValueError("scale cannot have both 'magnification' and 'mm_x' or 'mm_y'")
            elif 'mm_x' in scale and 'mm_y' not in scale:
                raise ValueError("scale must have both 'mm_x' and 'mm_y'")
            elif 'mm_x' not in scale and 'mm_y' in scale:
                raise ValueError("scale must have both 'mm_x' and 'mm_y'")


        if tile_size is not None:
            if not 'width' in tile_size or not 'height' in tile_size:
                raise ValueError("tile_size must be a dictionary with both 'width' and 'height'")
            if tile_size['width'] <= 0 or tile_size['height'] <= 0:
                raise ValueError("tile_size width and height must be greater than 0")

        if tile_overlap is not None:
            if 'x' in tile_overlap and 'y' in tile_overlap:
                if isinstance(tile_overlap['x'], int) and isinstance(tile_overlap['y'], int):
                    if tile_overlap['x'] < 0 or tile_overlap['y'] < 0:
                        raise ValueError("tile_overlap x and y must be greater than or equal to 0")
                elif isinstance(tile_overlap['x'], float) and isinstance(tile_overlap['y'], float):
                    if tile_overlap['x'] < 0 or tile_overlap['y'] < 0:
                        raise ValueError("tile_overlap x and y must be greater than or equal to 0")
                else:
                    raise ValueError("tile_overlap x and y must be both integers or both floats")
            else:
                raise ValueError("tile_overlap must be a dictionary with both 'x' and 'y'")

        self.dtype = dtype
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
        self.is_torch = False
        self.callable_arg_num = None
        self.transform = transform
        self.transform_save_mode = transform_save_mode
        self._worker_transform = None

        # Use the mask to determine the tiles if in tile mode
        if output_mode == 'tiles':
            # Use default tile source to determine slide dimensions
            self.slide_dimensions = calculate_slide_dimensions(self.source, region, scale, tile_size, source_scale)
            if tiles is None:
                tiles = return_relevant_tile_indexes_for_slide_dim(self.slide_dimensions, tile_overlap)
            if mask is not None:
                # If mask is a path, check if the path exists, attempt to open the image with PIL and convert to numpy array
                if isinstance(mask, str) and os.path.exists(mask):
                    mask = np.array(Image.open(mask))
                elif isinstance(mask, np.ndarray):
                    tiles = return_tile_slides_meeting_area_threshold(mask, self.slide_dimensions, tiles, area_threshold=area_threshold, threshold_mask=threshold_mask)
                else:
                    raise ValueError("Mask must be a file path that exists or a numpy array")
        elif output_mode == 'regions' and regions is not None:
            if isinstance(regions, list):
                regions = np.array(regions)
            # Use default region source to determine slide dimensions
            if region_size is not None:
                # Regions of form (left, top, width, height)
                if source_scale is not None:
                    raise ValueError("source_scale parammter must be None for regions mode")
                elif region is not None:
                    raise ValueError("region parameter must be None for regions mode")
                    
                self.slide_dimensions = calculate_slide_dimensions(self.source, region, scale, region_size, source_scale)

                # Check if region size is appropriate
                h_max = regions[:, 2].max()
                w_max = regions[:, 3].max()

                if h_max > self.slide_dimensions['tile_height_before_scaling'] or w_max > self.slide_dimensions['tile_width_before_scaling']:
                    raise ValueError("Desired region_size is smaller than needed for the regions provided \n Height, width max {}, {} \n Region height, width before scaling {}, {}".format(h_max, w_max, self.slide_dimensions['tile_height_before_scaling'], self.slide_dimensions['tile_width_before_scaling']))
            else:
                raise ValueError("region_size must be provided if output_mode is regions")
        else:
            raise ValueError("output mode must be either tiles or regions, If regions, regions must be provided")

        # Determine if the output changes based on the transform
        self._setup_out_dims()
        self._worker_transform = self._prepare_worker_transform(self.transform)

        n_possible_tiles = self.slide_dimensions['tile_target_range_x'] * self.slide_dimensions['tile_target_range_y']

        if output_mode == 'regions':
            assert isinstance(regions, list) or isinstance(regions, np.ndarray), "Regions must be a list or numpy array"
            self.read_kwargs = gen_read_args_for_regions(self.slide_dimensions, regions, edge=edge, chunk_mult=chunk_mult)
        elif output_mode == 'tiles':
            assert isinstance(tiles, list) or isinstance(tiles, np.ndarray), "Tiles must be a list or numpy array"
            self.read_kwargs = gen_read_args_for_tiles(n_possible_tiles, self.slide_dimensions, tiles, edge=edge, chunk_mult=chunk_mult)
        else:
            raise ValueError("Supplied output mode must be either tiles or regions")

        if randomize_chunks:
            random.seed(seed)
            random.shuffle(self.read_kwargs)

        # Setup the process pool after transform is registered
        from concurrent.futures import ProcessPoolExecutor, ALL_COMPLETED, wait
        self.pool = ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("fork"))
        self._initialize(batch, prefetch)

    def _setup_out_dims(self):
        self.out_dims = [self.batch, self.slide_dimensions['tile_size'][1], self.slide_dimensions['tile_size'][0], 3]
        
        if self.transform is not None:
            if self.transform_save_mode is not None and self.transform_save_mode not in ['tile_x_y', 'region_x_y']:
                raise ValueError("transform_save_mode must be either 'tile_x_y' or 'region_x_y'")
            self._setup_out_dims_for_transform()
            
    
        if self.nchw:
            self.out_dims = [self.out_dims[0], self.out_dims[3], self.out_dims[1], self.out_dims[2]]

    def _prepare_worker_transform(self, transform: Optional[Callable]):
        if transform is None:
            return None
        try:
            pickle.dumps(transform)
            return transform
        except Exception:
            from .eager_utils import eager_fn
            eager_fn.set_transform(transform)
            return _EAGER_FN_SENTINEL


    def _setup_out_dims_for_transform(self):
        test_data = np.zeros(self.out_dims[1:], dtype=self.dtype)
        if 'albumentations.core.composition.Compose' in str(type(self.transform)):
            test_out = self.transform(image=test_data)
            self.dtype = test_out['image'].dtype
            self.out_dims = tuple([self.out_dims[0]] + list(test_out['image'].shape))
            self.is_torch = False
        elif 'torchvision.transforms' in str(type(self.transform)) or 'torchvision.transforms.v2' in str(type(self.transform)):
            test_out = self.transform(test_data)
            self.dtype = test_out.dtype
            self.out_dims = tuple([self.out_dims[0]] + list(test_out.shape))
            self.is_torch = True
        elif isinstance(self.transform, Callable):
            # handle case if torch is used in the transform
            if 'torch' in str(type(self.transform)):
                try:
                    import torch
                    self.is_torch = True
                except Exception:
                    raise ImportError("torch must be installed to use a transform callable that returns a torch.Tensor")
            else:
                self.is_torch = False
            
            # Check the signature of the transform
            import inspect
            transform_signature = inspect.signature(self.transform)
            transform_parameters = transform_signature.parameters

            if len(transform_parameters) == 0:
                raise ValueError("Transform callable must have at least one parameter")
            elif len(transform_parameters) == 1:
                try:
                    test_out = self.transform(test_data)
                    if not isinstance(test_out, np.ndarray) and not isinstance(test_out, torch.Tensor):
                        raise ValueError("Transform callable must return a numpy array or torch.Tensor")
                    self.dtype = test_out.dtype
                    self.out_dims = tuple([self.out_dims[0]] + list(test_out.shape))
                    self.callable_arg_num = 1
                except Exception:
                    raise ValueError("Transform callable must have at least one parameter and return a numpy array or torch.Tensor")
            elif len(transform_parameters) == 2:
                raise ValueError("Transform callable must have one or three parameters")
            elif len(transform_parameters) == 3:
                try:
                    test_x = int(-1)
                    test_y = int(-1)
                    test_out = self.transform(test_data, test_x, test_y)
                    if self.is_torch and not isinstance(test_out, torch.Tensor):
                        raise ValueError("Transform callable must return a torch.Tensor if torch is used in the transform")
                    elif not isinstance(test_out, np.ndarray):
                        raise ValueError("Transform callable must return a numpy array or torch.Tensor")
                    self.dtype = test_out.dtype
                    self.out_dims = tuple([self.out_dims[0]] + list(test_out.shape))                    
                    self.callable_arg_num = 3
                except Exception as e:
                    raise ValueError("Transform callable must have three parameters and return a numpy array or torch.Tensor.  Error: {}".format(e))
            else:
                raise ValueError("Transform callable must have one or three parameters")
        else:
            raise ValueError("Transform must be a albumentations.core.composition.Compose or torchvision.transforms.v2._container.Compose object or a callable")

    def _initialize(self, batch: int, prefetch: int):
        self.prefetch = prefetch
        self.batch = batch
        self.queue = deque([])  # hold futures defining read operations
        self.overflow = 0  # count of tile overrun for latest batch
        self.pos = 0  # position in read_kwargs
        self._fill()

    def __iter__(self):
        return self
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.cleanup()
        finally:
            return False
    
    def cleanup(self, wait=True):
        """Clean up resources including the process pool and any remaining shared memory."""
        if hasattr(self, 'pool'):
            self.pool.shutdown(wait=wait, cancel_futures=True)
        # Clear any remaining shared arrays in the queue
        while self.queue:
            try:
                futures, tiles, batch_kwargs = self.queue.pop()
                # Wait for futures to complete before cleanup
                if futures:
                    wait(futures, timeout=5, return_when=ALL_COMPLETED)
                try:
                    # Prefer explicit close to avoid BufferError on shutdown
                    if hasattr(tiles, 'close'):
                        tiles.close()
                finally:
                    del tiles
            except Exception:
                pass  # Ignore cleanup errors
    
    def __del__(self):
        """Destructor to ensure cleanup on garbage collection."""
        try:
            # Use wait false to avoid waiting for submitted processes to execute
            # causing immediate exiting and returning to the main thread
            self.cleanup(wait=False)
        except Exception:
            pass  # Ignore cleanup errors during garbage collection
    
    def get_output_image_count(self):
        """
        Return the number of tiles that the eager iterator will yield.
        """
        count = 0
        for read_kwargs in self.read_kwargs:
            count += len(read_kwargs) 
        return count

    def __next__(self):
        """
        Return the next batch of tiles as a dictionary with keys defined below.
        """
        # TODO: develop method for random batch retrieval
        if self.pos >= len(self.read_kwargs) and not len(self.queue):
            if self.randomize_chunks:
                random.shuffle(self.read_kwargs)
            raise StopIteration

        # wait on the futures linked to the next batch
        try:
            futures, tiles, batch_read_kwargs = self.queue.pop()
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
            wait(futures_flat, timeout=None, return_when=ALL_COMPLETED)
            # Check for exceptions in futures - this will raise if any future had an exception
            for future in futures_flat:
                future.result()  # This will raise any exception that occurred in the worker process
            self._fill()
        except Exception as e:
            # Add exception for read operation in multiprocessing pool to allow user to be aware of potential issues
            # with their callable transform
            print("Exception in __next__: {}".format(e))
            self.pool.shutdown(wait=False, cancel_futures=True)
            raise Exception("Exception in __next__: {}".format(e))

        # last batch may only have partial size
        if self.pos == len(self.read_kwargs) and not len(self.queue):
            # Use resize_shm to adjust the shape of the shared memory to prevent issues if using pytorch tensors
            tiles.resize_shm([len(batch_read_kwargs), tiles.shape[1], tiles.shape[2], tiles.shape[3]])

        return self._tiles_and_read_kwargs_to_dict(tiles, batch_read_kwargs)
    
    def _tiles_and_read_kwargs_to_dict(self, tiles: SharedArray, read_kwargs: list):
        """
        Convert the read_kwargs list to a dictionary for simplified access to the relevant read arguments in a way that is more consistent with the original tileIterator.
        The dictionary is returned with the following keys:
            'format': 'numpy',
            'gx': left,
            'gy': top,
            'level_x': level_x,
            'level_y': level_y,
            'tile_position': {'level_x': level_x, 'level_y': level_y, 'region_x': region_x, 'region_y': region_y},
            'width': width,
            'height': height,
            'level': level,
            'magnification': magnification,
            'mm_x': mm_x,
            'mm_y': mm_y,
            'gwidth': gwidth,
            'gheight': gheight,

        Certain keys such as gx, gy, level_x, level_y, tile_position['level_x'], tile_position['level_y'], tile_position['base_x'], tile_position['base_y'] 
            are arrays of the same length as the number of tiles in the batch.

        :param read_kwargs: A list of read arguments used to produce the SharedNumpyArray.
        :return: A dictionary with the read arguments.
        """
        np_read_kwargs = np.array(read_kwargs)

        return {
            'format': 'numpy',
            'tile': tiles,
            'gx': np_read_kwargs[:, 6], # left
            'gy': np_read_kwargs[:, 4], # top
            'level_x': np_read_kwargs[:, 1],
            'level_y': np_read_kwargs[:, 0],
            'tile_position': {
                'level_x': np_read_kwargs[:, 1],
                'level_y': np_read_kwargs[:, 0],
                'region_x': np_read_kwargs[:, 3],
                'region_y': np_read_kwargs[:, 2],
            },
            'width': self.slide_dimensions['tile_size'][0], # right - left
            'height': self.slide_dimensions['tile_size'][1], # bottom - top
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
        transform: Optional[Callable] = None, 
        pad_mode: str = 'wsi_edge', 
        pad_fill_mode: str = 'default', 
        callable_arg_num: Optional[int] = None,
        transform_save_mode: Optional[str] = 'tile_x_y'
        ):
        """ 
        A static method used for reading regions from a tile source and filling the SharedNumpyArray with the results.
        
        :param source: A tile source object.
        :param dtype: The data type of the output array.
        :param nchw: A boolean controlling whether to return the output in NCHW format (True) or NHWC format (False).
            Will transpose transformed output as well.
        :param read_kwargs: A list of read arguments used to produce the SharedNumpyArray.
        :param sharrs: A list of SharedNumpyArray objects to be filled.
        :param offset: The offset of the current batch.
        """
        read_kwargs = np.array(read_kwargs)
        xlt = read_kwargs[:, 6].astype(np.uint)
        ytt = read_kwargs[:, 4].astype(np.uint)
        xrt = read_kwargs[:, 7].astype(np.uint)
        ybt = read_kwargs[:, 5].astype(np.uint)
        tile_y = read_kwargs[:, 2].astype(np.uint)
        tile_x = read_kwargs[:, 3].astype(np.uint)
        xr = np.min(xlt)
        yr = np.min(ytt)

        ybmax = np.max(ybt)
        xrmax = np.max(xrt)

        w = np.max(xrt) - xr
        h = np.max(ybt) - yr

        # Handle cases where supplied coordinates are not within margins of the image
        if xr < 0 or yr < 0:
            xlt = np.where(xlt > 0, xlt, 0).astype(np.uint)
            ytt = np.where(ytt > 0, ytt, 0).astype(np.uint)
            raise UserWarning("Negative coordinates.\n Defaulting to 0.\n Please check your input tiles/regions.\n  Read_kwargs {}".format(read_kwargs))
            # print("Negative coordinates.\n Defaulting to 0.\n Please check your input tiles/regions.\n  Read_kwargs {}".format(read_kwargs))
        if output_mode == 'regions' and (xrmax > slide_dimensions['base_size_x'] or ybmax > slide_dimensions['base_size_y']):
            ybt = np.where(ybt < slide_dimensions['base_size_y'], ybt, slide_dimensions['base_size_y']).astype(np.uint)
            xrt = np.where(xrt < slide_dimensions['base_size_x'], xrt, slide_dimensions['base_size_x']).astype(np.uint)
            raise UserWarning("Coordinates > image size.\n Defaulting to image boundaries.\n Please check your input tiles/regions. read_kwargs {}".format(read_kwargs))
            # print("Coordinates > image size.\n Defaulting to image boundaries.\n Please check your input tiles/regions. read_kwargs {}".format(read_kwargs))

        if output_mode == 'tiles':# tile size (x, y)
            xlo = np.floor(np.divide((xlt - xr), slide_dimensions['conv_mm_x'])).astype(np.uint)
            yto = np.floor(np.divide((ytt - yr), slide_dimensions['conv_mm_y'])).astype(np.uint)
            ho = yto + np.floor(np.divide((ybt - ytt), slide_dimensions['conv_mm_y'])).astype(np.uint)
            wo = xlo + np.floor(np.divide((xrt - xlt), slide_dimensions['conv_mm_x'])).astype(np.uint)
        elif output_mode == 'regions':

            xlo = np.floor(np.divide((xlt - xr), slide_dimensions['conv_mm_x'])).astype(np.uint)
            yto = np.floor(np.divide((ytt - yr) , slide_dimensions['conv_mm_y'])).astype(np.uint)
            ho = yto + np.floor(np.divide((ybt - ytt), slide_dimensions['conv_mm_y'])).astype(np.uint)
            wo = xlo + np.floor(np.divide((xrt - xlt), slide_dimensions['conv_mm_x'])).astype(np.uint)
        else:
            raise ValueError("Output mode not supported by read method.")

        h_max = np.max(ho).item()
        w_max = np.max(wo).item()

        no_scale = False
        #
        if slide_dimensions['scale_mode'] == 'mm':
            if slide_dimensions['base_mm_x'] == slide_dimensions['target_mm_x'] and slide_dimensions['base_mm_y'] == slide_dimensions['target_mm_y']:
                # no scaling needed
                no_scale = True
                kwargs = dict(
                    region=dict(left=xr, top=yr, width=w, height=h, units='base_pixels'),
                    format="numpy",
                )
            else:
                kwargs = dict(
                    sourceRegion=dict(left=xr.item(), top=yr.item(), width=w.item(), height=h.item(), units='base_pixels'),
                    targetScale=dict(mm_x=slide_dimensions['target_mm_x'], mm_y=slide_dimensions['target_mm_y'], units='mm'),
                    format="numpy",
                )
        elif slide_dimensions['scale_mode'] == 'mag':
            if slide_dimensions['base_magnification'] == slide_dimensions['target_magnification']:
                # no scaling needed
                no_scale = True
                kwargs = dict(
                    region=dict(left=xr.item(), top=yr.item(), width=w.item(), height=h.item(), units="base_pixels"),
                    format="numpy",
                )
            else:
                kwargs = dict(
                    sourceRegion = dict(left=xr.item(), top=yr.item(), width=w.item(), height=h.item(), units='base_pixels'),
                    targetScale = dict(magnification= slide_dimensions['target_magnification']),
                    format = "numpy"
                )
        else:
            raise ValueError("Invalid mode provided")

        if no_scale:
            chunk, _ = source.getRegion(**kwargs)  # type: ignore
        else:
            chunk, _ = source.getRegionAtAnotherScale(
                **kwargs  # type: ignore
            )

        assert isinstance(chunk, np.ndarray), "Returned chunk must be a numpy array"
        chunk = rgba2rgb(chunk)

        if output_mode == 'tiles':
            chunk = pad_chunk_if_necessary(slide_dimensions['base_size_x'], slide_dimensions['base_size_y'], chunk, xlt, xrt, ytt, ybt, w_max, h_max, pad_mode, pad_fill_mode)
            tiles = [
                chunk[yt : h, xl : w, :].astype(chunk.dtype)
                for (xl, w, yt, h) in zip(xlo, wo, yto, ho)
            ]
        elif output_mode == 'regions':
            tiles = [
                pad_tile(chunk[yt:h, xl:w, :].astype(chunk.dtype), slide_dimensions['tile_size'][0], slide_dimensions['tile_size'][1], pad_mode, pad_fill_mode)
                for (xl, w, yt, h) in zip(xlo, wo, yto, ho)
            ]

        # Don't change to target dtype until after transform
        if transform:
            if transform == _EAGER_FN_SENTINEL:
                from .eager_utils import eager_fn
                transform = eager_fn.get_transform()
                if transform is None:
                    raise ValueError("Eager transform not set in eager_utils.eager_fn")
            if 'albumentations.core.composition.Compose' in str(type(transform)):
                tiles = [
                    transform(image=tile)['image'].astype(dtype)
                    for tile in tiles
                ]
            elif 'torchvision.transforms' in str(type(transform)):                    
                tiles = [
                    transform(tile)
                    for tile in tiles
                ]
            else:
                # raise(Exception("Reached callable case"))
                if callable_arg_num == 1:
                    tiles = [
                        transform(tile).astype(dtype)
                        for tile in tiles
                    ]
                elif callable_arg_num == 3:
                    if transform_save_mode == 'tile_x_y':
                        tiles = [
                            transform(tile, x, y).astype(dtype)
                            for tile, x, y in zip(tiles, tile_x, tile_y)
                        ]
                    elif transform_save_mode == 'region_x_y':
                        tiles = [
                            transform(tile, x, y).astype(dtype)
                            for tile, x, y in zip(tiles, xlt, ytt)
                        ]

        for i, tile in enumerate(tiles):
            sharr_index, slice_index = divmod(offset + i, batch)

            # Expect transformer to control shape of output
            if nchw and isinstance(tile, np.ndarray):
                sharrs[sharr_index].insert(np.transpose(tile, [2, 0, 1]), slice_index)
            else:
                sharrs[sharr_index].insert(tile, slice_index)

    def _submitfn(self, read_kwargs: list, sharrs: list, offset: int):
        """
        Submit a read operation to the process pool.
        """

        return self.pool.submit(
            EagerIterator.read,
            self.source,
            self.dtype, # type: ignore
            self.nchw,
            read_kwargs,
            sharrs,
            offset,
            self.output_mode,
            self.batch,
            self.slide_dimensions,
            self._worker_transform,
            self.pad_mode,
            self.pad_fill_mode,
            self.callable_arg_num,
            self.transform_save_mode
        )      

    def _fill(self):
        """
        Fill the queue with read operations to be processed by the process pool.
        """
        def _fill_while():
            """
            A while loop used by the _fill method to fill the queue with read operations to be processed by the process pool.
            """
            while len(self.queue) < self.prefetch and self.pos < len(self.read_kwargs):
                """if the last read from the prior batch spanned batch boundaries then
                the leftmost element in self.queue contains the futures, shared array,
                and read_kwargs to start the current batch"""
                if self.overflow:
                    while len(self.queue) == 0:
                        time.sleep(0.01)
                    futures, tiles, batch_kwargs = self.queue.popleft()
                else:
                    """last read aligned with batch boundary, create new shared array,
                    and read_kwargs, futures containers"""
                    tiles = SharedArray(self.out_dims, self.dtype, self.is_torch)
                    futures = []
                    batch_kwargs = []

                """submit enough jobs to fill at least one batch - a single job may 
                fill multiple batches - or multiple jobs may be needed to fill one 
                batch"""
                offset = self.overflow
                batches = 1
                tiles = [tiles]
                while len(batch_kwargs) < self.batch and self.pos < len(
                        self.read_kwargs
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
                    tiles = [
                        *tiles,
                        *[
                            SharedArray(self.out_dims, self.dtype, self.is_torch)
                            for _ in range(batches - 1)
                        ],
                    ]

                    """submit job - read into first array in `tiles` at slice `offset`.
                    overflow to subsequent arrays if this read spans multiple batches.
                    if multiple reads are required to fill this batch then increment
                    the offset and submit another job on the next iteration"""
                    futures.append(self._submitfn(reads, tiles, offset))
                    offset = offset + len(reads)
                    batch_kwargs = batch_kwargs + reads
                    self.pos = self.pos + 1
                self.overflow = len(batch_kwargs) % self.batch

                """ if last read spans multiple batches, link that read's future
                to the other batches - also divide kwargs according to batch boundaries
                """
                futures = [futures] + (batches - 1) * [[futures[-1]]]
                batch_kwargs = [
                    batch_kwargs[i : i + self.batch]
                    for i in range(0, len(batch_kwargs), self.batch)
                ]

                # enqueue batches
                for f, t, b in zip(futures, tiles, batch_kwargs):
                    self.queue.appendleft((f, t, b))
        try:
            if self.is_torch:
                with _PyTorchThreadingContext():
                    _fill_while()
            else:
                _fill_while()

        except Exception as error:
            print("Exception in _fill: {}".format(error))
            self.pool.shutdown(wait=False, cancel_futures=True)
            raise Exception("Exception in _fill: {}".format(error))