import math, os, random
from typing import Optional, Tuple, Union, Callable
from collections import deque
from concurrent.futures import ProcessPoolExecutor, ALL_COMPLETED, wait
from .eager_utils.eager_shared_array import SharedArray
from .eager_utils.eager_pytorch_threading_context import _PyTorchThreadingContext

import numpy as np
from PIL import Image

from .. import tilesource

from .eager_utils.eager_image_modifications import pad_tile, pad_chunk_if_necessary, rgba2rgb

class EagerIterator:
    def __init__(
            self, 
            source: 'tilesource.TileSource',
            output_mode: str = 'tiles',
            scale_mode: str ='mag',
            overlap: Union[float, int] = 0,
            mask: Optional[Union[np.ndarray, str, os.PathLike]] = None,
            target_scale: Optional[Union[Tuple[float, float], float, Tuple[int, int], int]] = None,
            tile_size: Optional[Tuple[int, int]] = None,
            region_size: Optional[Tuple[int, int]] = None,
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
            ):
        """
        Initialize the EagerIterator class.  The EagerIterator class is an iterator intended for use in AI/ML applications.
        The eager iterator uses large_image source object which creates this iterator to read tiles or regions. The iterator
        provides numpy arrays of the requested tiles or regions.  The goal of this iterator is to simplify operations such
        as tiling and region extraction at specific resolutions/scales.  The format of output batches will always be numpy.     
        

        :param source: the tile source to use. this object should be provided a large_image tile source and will be provided
            by the large image library if you use the tile source's eagerIterator method.
        :param output_mode: A string corresponding to the output mode of the iterator. Can be either 'tiles' or 'regions'.  Defaults to 'tiles'.
        :param scale_mode: A string corresponding to the scale mode of the iterator. Can be either 'mag' or 'mm'.  Defaults to 'mag'.
        :param overlap: A float or integer defining the overlap in percentage between tiles.  If float, must be in range of 0 and 1.  Cannot be 1.  
            If integer, must be in range of 0 and the smallest dimension of the tile size.  Defaults to 0.
        :param mask: An optional numpy array or path to a 1 channel image that will be used to filter the tiles (only useful in tile mode).  This mask image is interpreted 
            based on two additional optional parameters: area_threshold and threshold_mask.  area_threshold is used to determine if a patch acquired from the mask
            contains enough signal to be used for a tile to be included in the output.  threshold_mask is used to determine if a pixel value within the mask corresponds to 
            signal.  If the mask is a uint8 array with values 0 to 1, then area_threshold will effectively be 1 instead of the default 100.  If the mask is a boolean array,
            then any True value will be considered signal.  Defaults to None.
        :param target_scale: An optional integer or tuple of floats defining the target scale produced for the iterator. If scale_mode is 'mag' can be an integer or float.
            If scale mode is 'mm' can be a tuple of (x, y) floating point numbers in mm.  Defaults ot None for base image scale.  Defaults to None.
        :param tile_size: An optional tuple of integers (x, y) defining the desired size in pixels of output tiles. If None, will use the default tile size of the slide.  Defaults to None.
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

        :returns: An iterator that returns a tuple of (SharedNumpyArray, dict) where SharedNumpyArray is a numpy array of a batch of tiles or regions based
            on the output_mode configured.  The numpy SharedNumpyArray corresponding the images can be accessed for use by using .view() (for example, batch[0].view())  
            read_kwargs is a list of the read arguments used to produce the SharedNumpyArray.  Keys that are not-consistent between tiles (such as gx, gy, level_x, level_y, etc.) will return a numpy array of values
              with values specific for tiles or regions returned in a batch.  The read_kwargs is a dictionary with the following keys:
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
            'gheight': gheight
        
        Given its specific use case, the eager iterator does not support all of the options available in the tileIterator.  
        The eager iterator does not support the following options:
            - region
            - scale
            - tile_overlap
            - format

        This iterator is experimental andmay not work with all tile sources.  Please consider the different expected inputs when attempting to use the eager iterator.
        """
        # Import eager_utils here to avoid attempting to load pykdtree when not needed
        from .eager_utils.eager_read_args import gen_read_args_for_tiles, gen_read_args_for_regions
        from .eager_utils.eager_wsi_operations import calculate_slide_dimensions, return_relevant_tile_indexes_for_slide_dim, return_tile_slides_meeting_area_threshold
    
        # Tile source becomes the source for the iterator allowing its options to be used
        self.source = source

        # Check for valid output mode
        if output_mode == 'regions' and not (isinstance(regions, list) or isinstance(regions, np.ndarray)):
            raise ValueError("output_mode set to 'regions'.  Regions must be a numpy array of the form  [[left, top, width, height], ...]")
        elif output_mode == 'tiles' and regions is not None:
            raise ValueError("output_mode set to 'tiles' but regions provided")

        if output_mode == 'regions' and pad_mode == 'wsi_edge':
            raise ValueError("pad_mode cannot be wsi_edge if output_mode is regions.  Please use pad_mode='equal' instead")
        
        if scale_mode not in ['mag', 'mm']:
            raise ValueError("scale_mode must be either 'mag' or 'mm'")

        self.dtype = dtype
        self.nchw = nchw
        self.edge = edge
        self.pool = ProcessPoolExecutor(max_workers=workers)
        self.transform = transform
        self.batch = batch
        self.output_mode = output_mode
        self.scale_mode = scale_mode
        self.pad_fill_mode = pad_fill_mode
        self.pad_mode = pad_mode
        self.chunk_mult = chunk_mult
        self.randomize_chunks = randomize_chunks
        self.seed = seed
        self.overlap = overlap
        self.target_scale = target_scale
        self.is_torch = False

        # Use the mask to determine the tiles if in tile mode
        if output_mode == 'tiles':
            # Use default tile source to determine slide dimensions
            self.slide_dimensions = calculate_slide_dimensions(self.source, scale_mode, target_scale, tile_size)
            if tiles is None:
                tiles = return_relevant_tile_indexes_for_slide_dim(self.slide_dimensions, overlap)
            if mask is not None:
                # If mask is a path, check if the path exists, attempt to open the image with PIL and convert to numpy array
                if isinstance(mask, str) and os.path.exists(mask):
                    mask = np.array(Image.open(mask))
                else:
                    raise ValueError("Mask file path must exist")

                # If mask is numpy array:q, use it to filter the tiles
                if isinstance(mask, np.ndarray):
                    tiles = return_tile_slides_meeting_area_threshold(mask, self.slide_dimensions, tiles, area_threshold=area_threshold, threshold_mask=threshold_mask)
                else:
                    raise ValueError("Mask must be a numpy array")
        elif output_mode == 'regions' and regions is not None:
            if isinstance(regions, list):
                regions = np.array(regions)
            # Use default region source to determine slide dimensions
            if region_size is not None:
                # Regions of form (left, top, width, height)
                self.slide_dimensions = calculate_slide_dimensions(self.source, scale_mode, target_scale, region_size)

                # Check if region size is appropriate
                h_max = regions[:, 2].max() / self.slide_dimensions['conv_mm_y']
                w_max = regions[:, 3].max() / self.slide_dimensions['conv_mm_x']

                if h_max > self.slide_dimensions['tile_height_before_scaling'] or w_max > self.slide_dimensions['tile_width_before_scaling']:
                    raise ValueError("Desired region_size is smaller than needed for the regions provided \n Height, width max {}, {} \n Region height, width before scaling {}, {}".format(h_max, w_max, self.slide_dimensions['tile_height_before_scaling'], self.slide_dimensions['tile_width_before_scaling']))
            else:
                raise ValueError("region_size must be provided if output_mode is regions")
        else:
            raise ValueError("output mode must be either tiles or regions, If regions, regions must be provided")

        # Transformer unfortunately cannot be used from pytorch v2 due to the way it is implemented
        self._setup_out_dims(self.slide_dimensions, transform)

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

        self._initialize(batch, prefetch)

    def _setup_out_dims(self, slide_dimensions: dict, transform: Optional[Callable] = None):
        self.out_dims = [self.batch, slide_dimensions['tile_size'][1], slide_dimensions['tile_size'][0], 3]
        if transform is not None:
            self._setup_out_dims_for_transform(self.out_dims, transform)
        if self.nchw:
            self.out_dims = [self.out_dims[0], self.out_dims[3], self.out_dims[1], self.out_dims[2]]


    def _setup_out_dims_for_transform(self, out_shape: Union[list, tuple], transform: Callable):
        test_data = np.zeros(out_shape[1:], dtype=self.dtype)
        if 'albumentations.core.composition.Compose' in str(type(transform)):
            test_out = transform(image=test_data)
            self.dtype = test_out['image'].dtype
            self.out_dims = tuple([self.out_dims[0]] + list(test_out['image'].shape))
            self.transform = transform
            self.is_torch = False
        elif 'torchvision.transforms.v2._container.Compose' in str(type(transform)):
            test_out = transform(test_data)
            self.dtype = test_out.dtype
            self.out_dims = tuple([self.out_dims[0]] + list(test_out.shape))
            self.transform = transform
            self.is_torch = True
        else:
            test_out = transform(test_data)
            if not isinstance(test_out, np.ndarray):
                raise ValueError(
                    """Transform must return a numpy array if not a albumentations.core.composition.Compose 
                    or torchvision.transforms.v2._container.Compose object""")
            self.dtype = test_out.dtype
            self.out_dims = tuple([self.out_dims[0]] + list(test_out.shape))
            self.transform = transform
            self.is_torch = False

    def _initialize(self, batch: int, prefetch: int):
        self.prefetch = prefetch
        self.batch = batch
        self.queue = deque([])  # hold futures defining read operations
        self.overflow = 0  # count of tile overrun for latest batch
        self.pos = 0  # position in read_kwargs
        self._fill()

    def __iter__(self):
        return self
    
    def get_output_image_count(self):
        count = 0
        for read_kwargs in self.read_kwargs:
            count += len(read_kwargs)
        return count

    def __next__(self):
        if self.pos >= len(self.read_kwargs) and not len(self.queue):
            if self.randomize_chunks:
                random.shuffle(self.read_kwargs)
            raise StopIteration

        # wait on the futures linked to the next batch
        try:
            futures, tiles, batch_read_kwargs = self.queue.pop()
            wait(futures, timeout=None, return_when=ALL_COMPLETED)
            self._fill()
        except:
            self.pool.shutdown(wait=False, cancel_futures=True)
            raise

        # last batch may only have partial size
        if self.pos == len(self.read_kwargs) and not len(self.queue):
            # Use resize_shm to adjust the shape of the shared memory to prevent issues if using pytorch tensors
            tiles.resize_shm([len(batch_read_kwargs), tiles.shape[1], tiles.shape[2], tiles.shape[3]])

        return tiles, self._read_kwargs_to_dict(batch_read_kwargs)
    
    def _read_kwargs_to_dict(self, read_kwargs: list):
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
    def read(source: 'tilesource.TileSource', dtype: np.dtype, nchw: bool, read_kwargs: list, sharrs: list, offset: int, output_mode: str, batch: int, slide_dimensions: dict, transform: Optional[Callable] = None, pad_mode: str = 'wsi_edge', pad_fill_mode: str = 'default'):
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
        try:
            # Format arrays of (x_coord, y_coord, y_bottom in org image, y_top in org image, x_left in org image, x_right in org image)
            # read followed by crops
            xlt = [k[6] for k in read_kwargs]
            ytt = [k[4] for k in read_kwargs]
            xrt = [k[7] for k in read_kwargs]
            ybt = [k[5] for k in read_kwargs]
            xr = min(xlt)
            yr = min(ytt)

            ybmax = max(ybt)
            xrmax = max(xrt)

            w = max(xrt) - xr
            h = max(ybt) - yr

            # Handle cases where supplied coordinates are not within margins of the image
            if xr < 0 or yr < 0:
                xlt = [k[6] if k[6] > 0 else 0 for k in read_kwargs]
                ytt = [k[4] if k[4] > 0 else 0 for k in read_kwargs]
                print("Negative coordinates.\n Defaulting to 0.\n Please check your input tiles/regions.\n  Read_kwargs {}".format(read_kwargs))
            if output_mode == 'regions' and (xrmax > slide_dimensions['base_size_x'] or ybmax > slide_dimensions['base_size_y']):
                ybt = [k[5] if k[5] < slide_dimensions['base_size_y'] else slide_dimensions['base_size_y'] for k in read_kwargs]
                xrt = [k[7] if k[7] < slide_dimensions['base_size_x'] else slide_dimensions['base_size_x'] for k in read_kwargs]
                print("Coordinates > image size.\n Defaulting to image boundaries.\n Please check your input tiles/regions. read_kwargs {}".format(read_kwargs))

            if output_mode == 'tiles':# tile size (x, y)
                xlo = [math.floor((x - xr) / slide_dimensions['conv_mm_x']) for x in xlt]
                yto = [math.floor((y - yr) / slide_dimensions['conv_mm_y']) for y in ytt]
                ho = [y + slide_dimensions['tile_size'][1] for y in yto]
                wo = [x + slide_dimensions['tile_size'][0] for x in xlo]
            elif output_mode == 'regions':
                xlo = [math.floor((x - xr) / slide_dimensions['conv_mm_x']) for x in xlt]
                yto = [math.floor((y - yr) / slide_dimensions['conv_mm_y']) for y in ytt]

                # min_xlo = min(xlo)
                # min_yto = min(yto)
                #
                # xlo2 = [x - min_xlo for x in xlo]
                # yto2 = [y - min_yto for y in yto]

                ho = [yto + math.floor((yb - yt) / slide_dimensions['conv_mm_y']) for (yto, yt, yb) in zip(yto, ytt, ybt)]
                wo = [xlo + math.floor((xr - xl) / slide_dimensions['conv_mm_x']) for (xlo, xl, xr) in zip(xlo, xlt, xrt)]
            else:
                raise ValueError("Output mode not supported by read method.")

            h_max = max(ho)
            w_max = max(wo)

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
                        sourceRegion=dict(left=xr, top=yr, width=w, height=h, units='base_pixels'),
                        targetScale=dict(mm_x=slide_dimensions['target_mm_x'], mm_y=slide_dimensions['target_mm_y'], units='mm'),
                        format="numpy",
                    )
            elif slide_dimensions['scale_mode'] == 'mag':
                if slide_dimensions['base_magnification'] == slide_dimensions['target_magnification']:
                    # no scaling needed
                    no_scale = True
                    kwargs = dict(
                        region=dict(left=xr, top=yr, width=w, height=h, units="base_pixels"),
                        format="numpy",
                    )
                else:
                    kwargs = dict(
                        sourceRegion = dict(left=xr, top=yr, width=w, height=h, units='base_pixels'),
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
            # elif output_mode == 'regions':
            #     chunk = pad_region_chunk(chunk, xlo, yto, wo, ho)

            if output_mode == 'tiles':
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
                if 'albumentations.core.composition.Compose' in str(type(transform)):
                    tiles = [
                        transform(image=tile)['image'].astype(dtype)
                        for tile in tiles
                    ]
                elif 'torchvision.transforms.v2._container.Compose' in str(type(transform)):                    
                    tiles = [
                        transform(tile).to(dtype)
                        for tile in tiles
                    ]
                else:
                    tiles = [
                        transform(tile).astype(dtype)
                        for tile in tiles
                    ]

            for i, tile in enumerate(tiles):
                sharr_index, slice_index = divmod(offset + i, batch)

                # Expect transformer to control shape of output
                if nchw and isinstance(tile, np.ndarray):
                    sharrs[sharr_index].insert(np.transpose(tile, [2, 0, 1]), slice_index)
                else:
                    sharrs[sharr_index].insert(tile, slice_index)

        except Exception as e:
            print("Failed to read {} with exception e {}".format(e, read_kwargs))
            raise(Exception("Failed to read {} with exception {}".format(read_kwargs, e)))

    def _submitfn(self, read_kwargs: list, sharrs: list, offset: int):
        return self.pool.submit(
            self.read,
            self.source,
            self.dtype, # type: ignore
            self.nchw,
            read_kwargs,
            sharrs,
            offset,
            self.output_mode,
            self.batch,
            self.slide_dimensions,
            self.transform,
            self.pad_mode,
            self.pad_fill_mode
        )
    
    # def _out_dims_adjust(self, out_dims: list):        

    def _fill(self):
        def _fill_while():
            while len(self.queue) < self.prefetch and self.pos < len(self.read_kwargs):
                """if the last read from the prior batch spanned batch boundaries then
                the leftmost element in self.queue contains the futures, shared array,
                and read_kwargs to start the current batch"""
                if self.overflow:
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
