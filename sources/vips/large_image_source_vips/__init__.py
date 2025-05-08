import logging
import math
import os
import threading
import uuid
from pathlib import Path

import cachetools
import numpy as np
import pyvips

from large_image import config
from large_image.cache_util import LruCacheMetaclass, _cacheClearFuncs, methodcache
from large_image.constants import (NEW_IMAGE_PATH_FLAG, TILE_FORMAT_NUMPY,
                                   GValueToDtype, SourcePriority,
                                   dtypeToGValue)
from large_image.exceptions import TileSourceError, TileSourceFileNotFoundError
from large_image.tilesource import FileTileSource
from large_image.tilesource.utilities import _imageToNumpy, _newFromFileLock, nearPowerOfTwo

logging.getLogger('pyvips').setLevel(logging.ERROR)

# Default to ignoring files with no extension and some specific extensions.
config.ConfigValues.setdefault(
    'source_vips_ignored_names', r'(^[^.]*|\.(yml|yaml|json|png|svs|mrxs))$')


def _clearVipsCache():
    oldfiles = pyvips.cache_get_max_files()
    oldmax = pyvips.cache_get_max()
    oldmem = pyvips.cache_get_max_mem()
    # print('Clearing vips cache: size %r, max files %r, max %r, mem %r' % (
    #     pyvips.cache_get_size(), oldfiles, oldmax, oldmem))
    pyvips.cache_set_max_files(0)
    # This shouldn't ever go to zero
    pyvips.cache_set_max(1)
    pyvips.cache_set_max_mem(0)
    pyvips.cache_set_max_files(oldfiles)
    pyvips.cache_set_max(oldmax)
    pyvips.cache_set_max_mem(oldmem)


_cacheClearFuncs.append(_clearVipsCache)


class VipsFileTileSource(FileTileSource, metaclass=LruCacheMetaclass):
    """
    Provides tile access to any libvips compatible file.
    """

    cacheName = 'tilesource'
    name = 'vips'
    extensions = {
        None: SourcePriority.LOW,
    }
    mimeTypes = {
        None: SourcePriority.FALLBACK,
    }
    newPriority = SourcePriority.MEDIUM

    _tileSize = 256

    def __init__(self, path, **kwargs):  # noqa
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: a filesystem path for the tile source.
        """
        super().__init__(path, **kwargs)
        self.addKnownExtensions()

        self._suffix = ''
        if str(path).startswith(NEW_IMAGE_PATH_FLAG):
            self._initNew(**kwargs)
            return
        self._largeImagePath = str(self._getLargeImagePath())
        self._editable = False

        config._ignoreSourceNames('vips', self._largeImagePath)
        try:
            with _newFromFileLock:
                self._image = pyvips.Image.new_from_file(self._largeImagePath)
        except pyvips.error.Error:
            if not os.path.isfile(self._largeImagePath):
                raise TileSourceFileNotFoundError(self._largeImagePath) from None
            msg = 'File cannot be opened via pyvips'
            raise TileSourceError(msg)
        # Ask pdfs to render at a higher resolution
        if ('vips-loader' in self._image.get_fields() and
                self._image.get('vips-loader') in {'pdfload'}):
            self._suffix = ',dpi=144'
            self._image = pyvips.Image.new_from_file(self._largeImagePath + '[dpi=300]')
        self.sizeX = self._image.width
        self.sizeY = self._image.height
        self.tileWidth = self.tileHeight = self._tileSize
        pages = 1
        if 'n-pages' in self._image.get_fields():
            pages = self._image.get('n-pages')
        self._frames = [0]
        self._lowres = {}
        for page in range(1, pages):
            subInputPath = self._largeImagePath + f'[page={page}{self._suffix}]'
            with _newFromFileLock:
                try:
                    subImage = pyvips.Image.new_from_file(subInputPath)
                except Exception:
                    continue
            if subImage.width == self.sizeX and subImage.height == self.sizeY:
                self._frames.append(page)
                continue
            if (self.sizeX - 16 < subImage.width <= self.sizeX and
                    self.sizeY - 16 < subImage.height <= self.sizeY):
                self._frames.append(page)
                continue
            if subImage.width * subImage.height < self.sizeX * self.sizeY:
                if (nearPowerOfTwo(self.sizeX, subImage.width) and
                        nearPowerOfTwo(self.sizeY, subImage.height)):
                    level = int(round(math.log(self.sizeX / subImage.width) / math.log(2)))
                    self._lowres.setdefault(len(self._frames) - 1, {})[level] = page
                continue
            self._frames = [page]
            self._lowres = {}
            self.sizeX = subImage.width
            self.sizeY = subImage.height
            try:
                self._image.close()
            except Exception:
                pass
            self._image = subImage
        self._checkLowerLevels()
        self.levels = int(max(1, math.ceil(math.log(
            float(max(self.sizeX, self.sizeY)) / self.tileWidth) / math.log(2)) + 1))
        if len(self._frames) > 1 or self._lowres is not None:
            self._recentFrames = cachetools.LRUCache(maxsize=6)
            self._frameLock = threading.RLock()

    def _checkLowerLevels(self):
        if (len(self._lowres) != len(self._frames) or
                min(len(v) for v in self._lowres.values()) !=
                max(len(v) for v in self._lowres.values()) or
                min(len(v) for v in self._lowres.values()) == 0):
            self._lowres = None
            if len(self._frames) == 1 and 'openslide.level-count' in self._image.get_fields():
                self._lowres = [{}]
                for oslevel in range(1, int(self._image.get('openslide.level-count'))):
                    with _newFromFileLock:
                        try:
                            subImage = pyvips.Image.new_from_file(
                                self._largeImagePath, level=oslevel)
                        except Exception:
                            continue
                        if subImage.width * subImage.height < self.sizeX * self.sizeY:
                            if (nearPowerOfTwo(self.sizeX, subImage.width) and
                                    nearPowerOfTwo(self.sizeY, subImage.height)):
                                level = int(round(math.log(
                                    self.sizeX / subImage.width) / math.log(2)))
                                self._lowres[0][level] = (self._frames[0], oslevel)
                if not len(self._lowres[0]):
                    self._lowres = None
        else:
            self._lowres = list(self._lowres.values())
        if self._lowres is not None:
            self._populatedLevels = len(self._lowres[0]) + 1

    def _initNew(self, **kwargs):
        """
        Initialize the tile class for creating a new image.
        """
        # Make unpickleable
        self._unpickleable = True
        self._largeImagePath = None
        self._image = None
        self.sizeX = self.sizeY = self.levels = 0
        self.tileWidth = self.tileHeight = self._tileSize
        self._frames = [0]
        self._lowres = None
        self._cacheValue = str(uuid.uuid4())
        self._output = None
        self._editable = True
        self._bandRanges = None
        self._addLock = threading.RLock()

    def getState(self):
        # Use the _cacheValue to avoid caching the source and tiles if we are
        # creating something new.
        if not hasattr(self, '_cacheValue'):
            return super().getState()
        return super().getState() + ',%s' % (self._cacheValue, )

    def getInternalMetadata(self, **kwargs):
        """
        Return additional known metadata about the tile source.  Data returned
        from this method is not guaranteed to be in any particular format or
        have specific values.

        :returns: a dictionary of data or None.
        """
        result = {}
        if not self._image:
            return result
        for key in self._image.get_fields():
            try:
                result[key] = self._image.get(key)
            except Exception:
                pass
        if len(self._frames) > 1:
            result['frames'] = []
            for idx in range(1, len(self._frames)):
                frameresult = {}
                result['frames'].append(frameresult)
                img = self._getFrameImage(idx)
                for key in img.get_fields():
                    try:
                        frameresult[key] = img.get(key)
                    except Exception:
                        pass
        return result

    def getMetadata(self):
        """
        Return a dictionary of metadata containing levels, sizeX, sizeY,
        tileWidth, tileHeight, magnification, mm_x, mm_y, and frames.

        :returns: metadata dictionary.
        """
        result = super().getMetadata()
        if len(self._frames) > 1:
            result['frames'] = [{} for _ in self._frames]
            self._addMetadataFrameInformation(result)
        return result

    def _getFrameImage(self, frame=0, lowres=None):
        """
        Get the vips image associated with a specific frame.

        :param frame: the 0-based frame to get.
        :param lowres: the lower resolution part of the frame
        :returns: a vips image.
        """
        if self._image is None and self._output:
            self._outputToImage()
        img = self._image
        if frame > 0 or lowres:
            with self._frameLock:
                key = (frame, lowres)
                frameval = self._frames[frame]
                params = {}
                if lowres is not None:
                    if isinstance(self._lowres[frame][lowres], tuple):
                        frameval = self._lowres[frame][lowres][0]
                        params = {'level': self._lowres[frame][lowres][1]}
                    else:
                        frameval = self._lowres[frame][lowres]
                if key not in self._recentFrames:
                    if frameval:
                        subpath = self._largeImagePath + f'[page={frameval}{self._suffix}]'
                    else:
                        subpath = self._largeImagePath
                    with _newFromFileLock:
                        img = pyvips.Image.new_from_file(subpath, **params)
                    self._recentFrames[key] = img
                else:
                    img = self._recentFrames[key]
        return img

    def getNativeMagnification(self):
        """
        Get the magnification at a particular level.

        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        return {
            'mm_x': self.mm_x,
            'mm_y': self.mm_y,
            'magnification': 0.01 / self.mm_x if self.mm_x else None,
        }

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False, **kwargs):
        frame = self._getFrame(**kwargs)
        self._xyzInRange(x, y, z, frame, len(self._frames))
        x0, y0, x1, y1, step = self._xyzToCorners(x, y, z)
        lowres = None
        if self._lowres and step > 1:
            use = 0
            for ll in self._lowres[frame].keys():
                if 2 ** ll <= step:
                    use = max(use, ll)
            if use:
                lowres = use
                div = 2 ** use
                x0 //= div
                y0 //= div
                x1 //= div
                y1 //= div
                step //= div
        img = self._getFrameImage(frame, lowres)
        tileimg = img.crop(min(x0, img.width), min(y0, img.height),
                           min(x1, img.width) - min(x0, img.width),
                           min(y1, img.height) - min(y0, img.height))
        try:
            if step != 1:
                tileimg = tileimg.resize(1.0 / step, kernel=pyvips.enums.Kernel.NEAREST, gap=0)
            tile = np.ndarray(
                buffer=tileimg.write_to_memory(),
                dtype=GValueToDtype[tileimg.format],
                shape=[tileimg.height, tileimg.width, tileimg.bands])
        except Exception:
            self.logger.exception('Failed to getTile')
            tile = np.zeros((1, 1))
        return self._outputTile(tile, TILE_FORMAT_NUMPY, x, y, z,
                                pilImageAllowed, numpyAllowed, **kwargs)

    def _checkEditable(self):
        """
        Raise an exception if this is not an editable image.
        """
        if not self._editable:
            msg = 'Not an editable image'
            raise TileSourceError(msg)

    def _updateBandRanges(self, tile):
        """
        Given a 3-d numpy array, update the tracked band ranges.

        :param tile: a numpy array.
        """
        amin = np.amin(tile, axis=(0, 1))
        amax = np.amax(tile, axis=(0, 1))
        if self._bandRanges is None:
            self._bandRanges = {
                'min': amin,
                'max': amax,
            }
        else:
            delta = len(self._bandRanges['min']) - len(amin)
            if delta > 0:
                amin = np.array(list(amin) + [0] * delta)
                amax = np.array(list(amax) + [0] * delta)
            elif delta < 0:
                self._bandRanges['min'] = np.array(list(self._bandRanges['min']) + [0] * -delta)
                self._bandRanges['max'] = np.array(list(self._bandRanges['max']) + [0] * -delta)
            self._bandRanges = {
                'min': np.minimum(self._bandRanges['min'], amin),
                'max': np.maximum(self._bandRanges['max'], amax),
            }

    def _addVipsImage(self, vimg, x=0, y=0):
        """
        Add a vips image to the output image.

        :param vimg: a vips image.
        :param x: location in destination for upper-left corner.
        :param y: location in destination for upper-left corner.
        """
        # Allow vips to persist the new tile to a temp file.  Otherwise, it may
        # try to hold all tiles in memory.
        vimgTemp = pyvips.Image.new_temp_file('%s.v')
        vimg.write(vimgTemp)
        vimg = vimgTemp
        with self._addLock:
            if self._output is None:
                self._output = {
                    'images': [],
                    'interp': vimg.interpretation,
                    'bands': vimg.bands,
                    'minx': None,
                    'miny': None,
                    'width': 0,
                    'height': 0,
                }
            self._output['images'].append({'image': vimg, 'x': x, 'y': y})
            if (self._output['interp'] != vimg.interpretation and
                    self._output['interp'] != pyvips.Interpretation.MULTIBAND):
                if vimg.interpretation in {
                        pyvips.Interpretation.MULTIBAND, pyvips.Interpretation.RGB}:
                    self._output['interp'] = vimg.interpretation
                if vimg.interpretation == pyvips.Interpretation.RGB and self._output['bands'] == 2:
                    self._output['bands'] = 4
            self._output['bands'] = max(self._output['bands'], vimg.bands)
            self._output['minx'] = min(
                self._output['minx'] if self._output['minx'] is not None else x, x)
            self._output['miny'] = min(
                self._output['miny'] if self._output['miny'] is not None else y, y)
            self._output['width'] = max(self._output['width'], x + vimg.width)
            self._output['height'] = max(self._output['height'], y + vimg.height)
            self._invalidateImage()

    def _invalidateImage(self):
        """
        Invalidate the tile and class cache
        """
        if self._output is not None:
            self._image = None
            w = self._output['width'] - min(0, self._output['minx'])
            h = self._output['height'] - min(0, self._output['miny'])
            w = max(self.minWidth or w, w)
            h = max(self.minHeight or h, h)
            self.sizeX = w
            self.sizeY = h
            self.levels = int(max(1, math.ceil(math.log(
                float(max(self.sizeX, self.sizeY)) / self.tileWidth) / math.log(2)) + 1))
            self._cacheValue = str(uuid.uuid4())

    def addTile(self, tile, x=0, y=0, mask=None, interpretation=None):
        """
        Add a numpy or image tile to the image, expanding the image as needed
        to accommodate it.  Note that x and y can be negative.  If so, the
        output image (and internal memory access of the image) will act as if
        the 0, 0 point is the most negative position.  Cropping is applied
        after this offset.

        :param tile: a numpy array, PIL Image, vips image, or a binary string
            with an image.  The numpy array can have 2 or 3 dimensions.
        :param x: location in destination for upper-left corner.
        :param y: location in destination for upper-left corner.
        :param mask: a 2-d numpy array (or 3-d if the last dimension is 1).
            If specified, areas where the mask is false will not be altered.
        :param interpretation: one of the pyvips.enums.Interpretation or 'L',
            'LA', 'RGB', "RGBA'.  This defaults to RGB/RGBA for 3/4 channel
            images and L/LA for 1/2 channels.  The special value 'pixelmap'
            will convert a 1 channel integer to a 3 channel RGB map.  For
            images which are not 1 or 3 bands with an optional alpha, specify
            MULTIBAND.  In this case, the mask option cannot be used.
        """
        self._checkEditable()
        if not isinstance(tile, pyvips.vimage.Image):
            tile, mode = _imageToNumpy(tile)
            interpretation = interpretation or mode
        with self._addLock:
            self._updateBandRanges(tile)
        if interpretation == 'pixelmap':
            with self._addLock:
                self._interpretation = 'pixelmap'
            tile = np.dstack((
                (tile % 256).astype(int),
                (tile / 256).astype(int) % 256,
                (tile / 65536).astype(int) % 256)).astype('B')
            interpretation = pyvips.enums.Interpretation.RGB
        if interpretation != pyvips.Interpretation.MULTIBAND and tile.shape[2] in {1, 3}:
            newarr = np.zeros(
                (tile.shape[0], tile.shape[1], tile.shape[2] + 1), dtype=tile.dtype)
            newarr[:, :, :tile.shape[2]] = tile
            newarr[:, :, -1] = min(np.iinfo(
                tile.dtype).max, 255) if tile.dtype.kind in 'iu' else 255
            tile = newarr
        if mask is not None:
            if len(mask.shape) == 3:
                mask = np.logical_or.reduce(mask, axis=2)
            if tile.shape[2] in {2, 4}:
                tile[:, :, -1] *= mask.astype(bool)
            else:
                msg = 'Cannot apply a mask if the source is not 1 or 3 channels.'
                raise TileSourceError(msg)
        if tile.dtype.char not in dtypeToGValue:
            tile = tile.astype(float)
        vimg = pyvips.Image.new_from_memory(
            np.ascontiguousarray(tile).data,
            tile.shape[1], tile.shape[0], tile.shape[2],
            dtypeToGValue[tile.dtype.char])
        interpretation = interpretation if any(
            v == interpretation for k, v in pyvips.enums.Interpretation.__dict__.items()
            if not k.startswith('_')) else (
            pyvips.Interpretation.B_W if tile.shape[2] <= 2 else (
                pyvips.Interpretation.RGB if tile.shape[2] <= 4 else
                pyvips.Interpretation.MULTIBAND))
        vimg = vimg.copy(interpretation=interpretation)
        # The alpha channel is [0, 255] if we created it (which is true if the
        # band range doesn't include it)
        self._addVipsImage(vimg, x, y)

    def _getVipsFormat(self):
        """
        Get the recommended vips format for the output image based on the
        band range and the interpretation.

        :returns: a vips BandFormat.
        """
        bmin, bmax = min(self._bandRanges['min']), max(self._bandRanges['max'])
        if getattr(self, '_interpretation', None) == 'pixelmap':
            format = pyvips.enums.BandFormat.UCHAR
        elif bmin >= -1 and bmax <= 1:
            format = pyvips.enums.BandFormat.FLOAT
        elif bmin >= 0 and bmax < 2 ** 8:
            format = pyvips.enums.BandFormat.UCHAR
        elif bmin >= 0 and bmax < 2 ** 16:
            format = pyvips.enums.BandFormat.USHORT
        elif bmin >= 0 and bmax < 2 ** 32:
            format = pyvips.enums.BandFormat.UINT
        elif bmin < 0 and bmin >= -(2 ** 7) and bmax < 2 ** 7:
            format = pyvips.enums.BandFormat.CHAR
        elif bmin < 0 and bmin >= -(2 ** 15) and bmax < 2 ** 15:
            format = pyvips.enums.BandFormat.SHORT
        elif bmin < 0 and bmin >= -(2 ** 31) and bmax < 2 ** 31:
            format = pyvips.enums.BandFormat.INT
        else:
            format = pyvips.enums.BandFormat.FLOAT
        return format

    def _outputToImage(self):
        """
        Create a vips image that pipelines all of the pieces we have into a
        single image.  This makes an image that is large enough to hold all of
        the pieces and is an appropriate datatype to represent the range of
        values that are present.  For pixelmaps, this will be RGB 8-bit.  An
        alpha channel is always included unless the intrepretation is
        multichannel.
        """
        with self._addLock:
            bands = self._output['bands']
            if bands in {1, 3}:
                bands += 1
            img = pyvips.Image.black(self.sizeX, self.sizeY, bands=bands)
            if self.mm_x or self.mm_y:
                img = img.copy(
                    xres=1.0 / (self.mm_x if self.mm_x else self._mm_y),
                    yres=1.0 / (self.mm_y if self.mm_y else self._mm_x))
            format = self._getVipsFormat()
            if img.format != format:
                img = img.cast(format)
            baseimg = img.copy(interpretation=self._output['interp'], format=format)

            leaves = math.ceil(len(self._output['images']) ** (1. / 3))
            img = baseimg.copy()
            trunk = baseimg.copy()
            branch = baseimg.copy()
            for idx, entry in enumerate(self._output['images']):
                entryimage = entry['image']
                if img.format == 'float' and entry['image'].format == 'double':
                    entryimage = entryimage.cast(img.format)
                branch = branch.composite(
                    entryimage, pyvips.BlendMode.OVER,
                    x=entry['x'] - min(0, self._output['minx']),
                    y=entry['y'] - min(0, self._output['miny']))
                if not ((idx + 1) % leaves) or idx + 1 == len(self._output['images']):
                    trunk = trunk.composite(branch, pyvips.BlendMode.OVER, x=0, y=0)
                    branch = baseimg.copy()
                if not ((idx + 1) % (leaves * leaves)) or idx + 1 == len(self._output['images']):
                    img = img.composite(trunk, pyvips.BlendMode.OVER, x=0, y=0)
                    trunk = baseimg.copy()
            self._image = img

    def write(self, path, lossy=True, alpha=True, overwriteAllowed=True, vips_kwargs=None):
        """
        Output the current image to a file.

        :param path: output path.
        :param lossy: if false, emit a lossless file.
        :param alpha: True if an alpha channel is allowed.
        :param overwriteAllowed: if False, raise an exception if the output
            path exists.
        :param vips_kwargs: if not None, save the image using these kwargs to
            the write_to_file function instead of the automatically chosen
            ones.  In this case, lossy is ignored and all vips options must be
            manually specified.
        """
        if not overwriteAllowed and os.path.exists(path):
            raise TileSourceError('Output path exists (%s)' % str(path))
        with self._addLock:
            img = self._getFrameImage(0)
            # TODO: set image description: e.g.,
            # img.set_type(
            #   pyvips.GValue.gstr_type, 'image-description',
            #   json.dumps(dict(vars(opts), indexCount=found)))
            if getattr(self, '_interpretation', None) == 'pixelmap':
                img = img[:3]
            elif (not alpha and getattr(self, '_output', {}).get(
                    'interp') != pyvips.Interpretation.MULTIBAND):
                img = img[:-1]
        if self.crop:
            x, y, w, h = self._crop
            w = max(0, min(img.width - x, w))
            h = max(0, min(img.height - y, h))
            x = min(x, img.width)
            y = min(y, img.height)
            img = img.crop(x, y, w, h)
        pathIsTiff = Path(path).suffix.lower() in {'.tif', '.tiff'}
        pixels = img.width * img.height
        if vips_kwargs is not None or not pathIsTiff:
            img.write_to_file(path, **(vips_kwargs or {}))
        elif not lossy:
            img.write_to_file(
                path, tile_width=self.tileWidth, tile_height=self.tileHeight,
                tile=True, pyramid=True, bigtiff=pixels >= 2 * 1024 ** 3,
                region_shrink='nearest', compression='lzw', predictor='horizontal')
        else:
            img.write_to_file(
                path, tile_width=self.tileWidth, tile_height=self.tileHeight,
                tile=True, pyramid=True, bigtiff=pixels >= 2 * 1024 ** 3,
                compression='jpeg', Q=90)

    @property
    def crop(self):
        """
        Crop only applies to the output file, not the internal data access.

        It consists of x, y, w, h in pixels.
        """
        return getattr(self, '_crop', None)

    @crop.setter
    def crop(self, value):
        self._checkEditable()
        if value is None:
            self._crop = None
            return
        x, y, w, h = value
        x = int(x)
        y = int(y)
        w = int(w)
        h = int(h)
        if x < 0 or y < 0 or w <= 0 or h <= 0:
            msg = 'Crop must have non-negative x, y and positive w, h'
            raise TileSourceError(msg)
        self._crop = (x, y, w, h)

    @property
    def minWidth(self):
        return getattr(self, '_minWidth', None)

    @minWidth.setter
    def minWidth(self, value):
        self._checkEditable()
        value = int(value) if value is not None else None
        if value is not None and value <= 0:
            msg = 'minWidth must be positive or None'
            raise TileSourceError(msg)
        if value != getattr(self, '_minWidth', None):
            self._minWidth = value
            self._invalidateImage()

    @property
    def minHeight(self):
        return getattr(self, '_minHeight', None)

    @minHeight.setter
    def minHeight(self, value):
        self._checkEditable()
        value = int(value) if value is not None else None
        if value is not None and value <= 0:
            msg = 'minHeight must be positive or None'
            raise TileSourceError(msg)
        if value != getattr(self, '_minHeight', None):
            self._minHeight = value
            self._invalidateImage()

    @property
    def mm_x(self):
        if getattr(self, '_mm_x', None):
            return self._mm_x
        xres = 0
        if self._image:
            xres = self._image.get('xres') or 0
        return 1.0 / xres if xres and xres != 1 else None

    @mm_x.setter
    def mm_x(self, value):
        self._checkEditable()
        value = float(value) if value is not None else None
        if value is not None and value <= 0:
            msg = 'mm_x must be positive or None'
            raise TileSourceError(msg)
        if value != getattr(self, '_minHeight', None):
            self._mm_x = value
            self._invalidateImage()

    @property
    def mm_y(self):
        if getattr(self, '_mm_y', None):
            return self._mm_y
        yres = 0
        if self._image:
            yres = self._image.get('yres') or 0
        return 1.0 / yres if yres and yres != 1 else None

    @mm_y.setter
    def mm_y(self, value):
        self._checkEditable()
        value = float(value) if value is not None else None
        if value is not None and value <= 0:
            msg = 'mm_y must be positive or None'
            raise TileSourceError(msg)
        if value != getattr(self, '_minHeight', None):
            self._mm_y = value
            self._invalidateImage()

    @property
    def bandRanges(self):
        return getattr(self, '_bandRanges', None)

    @property
    def bandFormat(self):
        if not self._editable:
            return self._image.format
        return self._getVipsFormat()
    # TODO: specify bit depth / bandFormat explicitly

    @property
    def origin(self):
        if not self._editable:
            return {'x': 0, 'y': 0}
        return {'x': min(0, self._output['minx'] or 0),
                'y': min(0, self._output['miny'] or 0)}

    @classmethod
    def addKnownExtensions(cls):
        if not hasattr(cls, '_addedExtensions'):
            cls._addedExtensions = True
            cls.extensions = cls.extensions.copy()
            for dotext in pyvips.base.get_suffixes():
                ext = dotext.lstrip('.')
                if ext not in cls.extensions:
                    cls.extensions[ext] = SourcePriority.IMPLICIT


def open(*args, **kwargs):
    """Create an instance of the module class."""
    return VipsFileTileSource(*args, **kwargs)


def canRead(*args, **kwargs):
    """Check if an input can be read by the module class."""
    return VipsFileTileSource.canRead(*args, **kwargs)


def new(*args, **kwargs):
    """
    Create a new image, collecting the results from patches of numpy arrays or
    smaller images.
    """
    return VipsFileTileSource(NEW_IMAGE_PATH_FLAG + str(uuid.uuid4()), *args, **kwargs)
