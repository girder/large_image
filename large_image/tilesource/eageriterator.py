import math, os, random
from typing import Optional, Tuple, Union
from collections import deque
from concurrent.futures import ProcessPoolExecutor, ALL_COMPLETED, wait
from .eager_utils.eager_shared_numpy import SharedNumpyArray

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
            mask: np.ndarray | str | os.PathLike = None,
            target_scale: Optional[Tuple[float, float]] | Optional[float] = None,
            tile_size: Optional[Tuple[int, int]] = None,
            region_size: Optional[Tuple[int, int]] = None,
            dtype: np.dtype = np.uint8,
            chunk_mult: int = 2,
            edge: bool = False,
            pad_mode: str = 'wsi_edge',
            pad_fill_mode: str = 'default',
            nchw: bool = False,
            batch: int = 64,
            prefetch: int = 16,
            workers: int = 16,
            tiles: list | np.ndarray = None,
            regions: list | np.ndarray = None,
            transformer: callable = None,
            randomize_chunks: bool = False,
            seed: int = 42,
            area_threshold: float = 0.25,
            threshold_mask: int = 100,
            ):
        """
        Initialize the eager iterator class.  The eager iterator class is an iterator intended for use in AI/ML applications.
        The eager iterator uses large_image source object which creates this iterator to read tiles or regions. The iterator
        provides numpy arrays of the requested tiles or regions.  The goal of this iterator is to simplify operations such
        as tiling and region extraction at specific resolutions/scales.

        :param source: the tile source to use. this object should be provided a large_image tile source and will be provided
            by the large image library if you use the tile source's eagerIterator method.
        :param output_mode: A string corresponding to the output mode of the iterator. Can be either 'tiles' or 'regions'.
        :param scale_mode: A string corresponding to the scale mode of the iterator. Can be either 'mag' or 'mm'.
        :param overlap: A float defining the overlap in percentage between tiles. Defaults to 0.  If float, must be in range of 0 and 1.  Cannot be 1.  
            If integer, must be in range of 0 and the smallest dimension of the tile size.
        :param mask: A numpy array or path to a 1 channel image that will be used to filter the tiles.
        :param target_scale: An integer or tuple of floats defining the target scale produced for the iterator. If scale_mode is 'mag' can be an integer or float.
            If scale mode is 'mm' can be a tuple of (x, y) floating point numbers in mm.  Defaults ot None for base image scale.
        :param tile_size: A tuple of integers (x, y) defining the desired size in pixels of output tiles. If None, will use the default tile size of the slide.
        :param region_size: A tuple of integers (x, y) defining the desired size in pixels of output regions. If None, will use the default region size of the slide.
        :param dtype: A numpy data type for the output image batch. Defaults to np.uint8.
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
        :param regions: A numpy array in the shape of [n, 4]  where top = [:,0], left = [:,1], height = [:,2 width = [:,3]. Only used in output_mode 'regions'.  
            Defaults to None.
        :param transformer: A callable albumentations composed transform to be applied to the tiles. Defaults to None.
        :param randomize_chunks: A boolean controlling whether to randomize order of the chunks to make the output batches more random. Defaults to False.
        :param seed: A seed for the random number generator. Defaults to 42.
        :param area_threshold: A float defining the area threshold for the mask to be used to filter the tiles.  It is a value between 0 and 1 defining the portion 
            of the tile that must be signal defined in the mask to be included in the output.  Defaults to 0.25.
        :param threshold_mask: An integer defining the pixel value threshold for for a pixel to contribute to signal as defined in the mask.  Defaults to 100.

        :yields: An iterator that returns a tuple of (SharedNumpyArray, read_kwargs) where SharedNumpyArray is a numpy array of a batch of tiles or regions based
            on the output_mode configured.  The numpy arrays corresponding the images can be accessed for use by using .view() (for example, batch[0].view())  
            read_kwargs is a list of the read arguments used to produce the SharedNumpyArray.  The read_kwargs is a numpy array with the following sequence of values
            for output_mode = 'tiles': [original_tile_y, original_tile_x, output_tile_y, output_tile_x, top, bottom, left, right].  The read_kwargs is a numpy array with the
            following values for output_mode = 'regions': [original_tile_y, original_tile_x, center_y, center_x, top, bottom, left, right].  The original_tile_y, 
            original_tile_x are derived from the tile grid of the original base image.  The output_tile_y, output_tile_x are derived from a grid created using the 
            scaling configuration provided.  Center_y, center_x are the center pixel coordinates in the original base image.  Top, bottom, left, and right are the pixel 
            coordinates of the base image.
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
        self.transformer = transformer
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
        self._setup_out_dims(self.slide_dimensions, transformer)

        n_possible_tiles = self.slide_dimensions['tile_target_range_x'] * self.slide_dimensions['tile_target_range_y']

        if output_mode == 'regions':
            self.read_kwargs = gen_read_args_for_regions(self.slide_dimensions, regions, edge=edge, chunk_mult=chunk_mult)
        elif output_mode == 'tiles':
            self.read_kwargs = gen_read_args_for_tiles(n_possible_tiles, self.slide_dimensions, tiles, edge=edge, chunk_mult=chunk_mult)
        else:
            raise ValueError("Supplied output mode must be either tiles or regions")

        if randomize_chunks:
            random.seed(seed)
            random.shuffle(self.read_kwargs)

        self._initialize(batch, prefetch)

    def _setup_out_dims(self, slide_dimensions: dict, transformer: callable):
        self.out_dims = [self.batch, slide_dimensions['tile_size'][1], slide_dimensions['tile_size'][0], 3]
        if transformer is not None:
            self._setup_out_dims_for_transformer(self.out_dims, transformer)
        if self.nchw:
            self.out_dims = [self.out_dims[0], self.out_dims[3], self.out_dims[1], self.out_dims[2]]


    def _setup_out_dims_for_transformer(self, out_shape: Union[list, tuple], transformer: callable):
        test_data = np.zeros(out_shape, dtype=self.dtype)
        test_out = transformer(image=test_data)
        self.dtype = test_out['image'].dtype
        self.out_dims = test_out['image'].shape
        self.transformer = transformer


    def _initialize(self, batch: int, prefetch: int):
        self.prefetch = prefetch
        self.batch = batch
        self.queue = deque([])  # hold futures defining read operations
        self.overflow = 0  # count of tile overrun for latest batch
        self.pos = 0  # position in read_kwargs
        self._fill()

    def __iter__(self):
        return self

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
            tiles.shape = [len(batch_read_kwargs), tiles.shape[1], tiles.shape[2], tiles.shape[3]]

        return tiles, self._read_kwargs_to_dict(batch_read_kwargs)
    
    def _read_kwargs_to_dict(self, read_kwargs: list):
        read_kwargs = np.array(read_kwargs)

        return {
            'format': 'numpy',
            'gx': read_kwargs[:, 6], # left
            'gy': read_kwargs[:, 4], # top
            'level_x': read_kwargs[:, 3],
            'level_y': read_kwargs[:, 2],
            'tile_position': {
                'level_x': read_kwargs[:, 3],
                'level_y': read_kwargs[:, 2],
                'base_x': read_kwargs[:, 1],
                'base_y': read_kwargs[:, 0],
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
    def read(source: 'tilesource.TileSource', dtype: np.dtype, nchw: bool, read_kwargs: list, sharrs: list, offset: int, output_mode: str, batch: int, slide_dimensions: dict, transformer: callable, pad_mode: str, pad_fill_mode: str):
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
            if slide_dimensions['mode'] == 'mm':
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
            elif slide_dimensions['mode'] == 'mag':
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
                chunk, _ = source.getRegion(**kwargs)
            else:
                chunk, _ = source.getRegionAtAnotherScale(
                    **kwargs
                )

            chunk = rgba2rgb(chunk)

            if output_mode == 'tiles':
                chunk = pad_chunk_if_necessary(slide_dimensions['base_size_x'], slide_dimensions['base_size_y'], chunk, xlt, xrt, ytt, ybt, w_max, h_max, pad_mode, pad_fill_mode)
            # elif output_mode == 'regions':
            #     chunk = pad_region_chunk(chunk, xlo, yto, wo, ho)

            if output_mode == 'tiles':
                tiles = [
                    chunk[yt : h, xl : w, :].astype(dtype)
                    for (xl, w, yt, h) in zip(xlo, wo, yto, ho)
                ]
            elif output_mode == 'regions':
                tiles = [
                    pad_tile(chunk[yt:h, xl:w, :].astype(dtype), slide_dimensions['tile_size'][0], slide_dimensions['tile_size'][1], pad_mode, pad_fill_mode)
                    for (xl, w, yt, h) in zip(xlo, wo, yto, ho)
                ]

            if transformer:
                tiles = [
                    transformer(image=tile)['image']
                    for tile in tiles
                ]

                # tiles = []
                #
                # for i, (xl, w, yt, h) in enumerate(zip(xlo, wo, yto, ho)):
                #     tile = chunk[yt : h, xl : w, :]
                #     tiles.append(tile)

            for i, tile in enumerate(tiles):
                sharr_index, slice_index = divmod(offset + i, batch)

                # Expect transformer to control shape of output
                if nchw:
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
            self.dtype,
            self.nchw,
            read_kwargs,
            sharrs,
            offset,
            self.output_mode,
            self.batch,
            self.slide_dimensions,
            self.transformer,
            self.pad_mode,
            self.pad_fill_mode
        )

    def _fill(self):
        try:
            while len(self.queue) < self.prefetch and self.pos < len(self.read_kwargs):
                """if the last read from the prior batch spanned batch boundaries then
                the leftmost element in self.queue contains the futures, shared array,
                and read_kwargs to start the current batch"""
                if self.overflow:
                    futures, tiles, batch_kwargs = self.queue.popleft()
                else:
                    """last read aligned with batch boundary, create new shared array,
                    and read_kwargs, futures containers"""
                    tiles = SharedNumpyArray(self.out_dims, self.dtype)
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

                    # create additional arrays if this read spans multiple batches
                    tiles = [
                        *tiles,
                        *[
                            SharedNumpyArray(self.out_dims, self.dtype)
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

        except Exception as error:
            print("Exception in _fill: {}".format(error))
            self.pool.shutdown(wait=False, cancel_futures=True)
            raise Exception("Exception in _fill: {}".format(error))
