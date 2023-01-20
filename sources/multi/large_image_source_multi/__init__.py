import builtins
import copy
import itertools
import json
import math
import os
import re
import warnings
from pathlib import Path

import jsonschema
import numpy
import yaml

import large_image
from large_image.cache_util import LruCacheMetaclass, methodcache
from large_image.constants import TILE_FORMAT_NUMPY, SourcePriority
from large_image.exceptions import TileSourceError, TileSourceFileNotFoundError
from large_image.tilesource import FileTileSource
from large_image.tilesource.utilities import _makeSameChannelDepth

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _importlib_version
except ImportError:
    from importlib_metadata import PackageNotFoundError
    from importlib_metadata import version as _importlib_version
try:
    __version__ = _importlib_version(__name__)
except PackageNotFoundError:
    # package is not installed
    pass


warnings.filterwarnings('ignore', category=UserWarning, module='glymur')

SourceEntrySchema = {
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'name': {'type': 'string'},
        'description': {'type': 'string'},
        'path': {
            'decription':
                'The relative path, including file name if pathPattern is not '
                'specified.  The relative path excluding file name if '
                'pathPattern is specified.  Or, girder://id for Girder '
                'sources.  If a specific tile source is specified that does '
                'not need an actual path, the special value of `__none__` can '
                'be used to bypass checking for an actual file.',
            'type': 'string',
        },
        'pathPattern': {
            'description':
                'If specified, file names in the path are matched to this '
                'regular expression, sorted in C-sort order.  This can '
                'populate other properties via named expressions, e.g., '
                'base_(?<xy>\\d+).png.  Add 1 to the name for 1-based '
                'numerical values.',
            'type': 'string',
        },
        'sourceName': {
            'description':
                'Require a specific source by name.  This is one of the '
                'large_image source names (e.g., this one is "multi".',
            'type': 'string',
        },
        # 'projection': {
        #     'description':
        #         'If specified, the source is treated as non-geospatial and '
        #         'then a projection is added.  Set to None/null to use its '
        #         'own projection if a overall projection was specified.',
        #     'type': 'string',
        # },
        # corner points in the projection?
        'frame': {
            'description':
                'Base value for all frames; only use this if the data does '
                'not conceptually have z, t, xy, or c arrangement.',
            'type': 'integer',
            'minimum': 0,
        },
        'z': {
            'description': 'Base value for all frames',
            'type': 'integer',
            'minimum': 0,
        },
        't': {
            'description': 'Base value for all frames',
            'type': 'integer',
            'minimum': 0,
        },
        'xy': {
            'description': 'Base value for all frames',
            'type': 'integer',
            'minimum': 0,
        },
        'c': {
            'description': 'Base value for all frames',
            'type': 'integer',
            'minimum': 0,
        },
        'zSet': {
            'description': 'Override value for frame',
            'type': 'integer',
            'minimum': 0,
        },
        'tSet': {
            'description': 'Override value for frame',
            'type': 'integer',
            'minimum': 0,
        },
        'xySet': {
            'description': 'Override value for frame',
            'type': 'integer',
            'minimum': 0,
        },
        'cSet': {
            'description': 'Override value for frame',
            'type': 'integer',
            'minimum': 0,
        },
        'zValues': {
            'description':
                'The numerical z position of the different z indices of the '
                'source.  If only one value is specified, other indices are '
                'shifted based on the source.  If fewer values are given than '
                'z indices, the last two value given imply a stride for the '
                'remainder.',
            'type': 'array',
            'items': {'type': 'number'},
            'minItems': 1,
        },
        'tValues': {
            'description':
                'The numerical t position of the different t indices of the '
                'source.  If only one value is specified, other indices are '
                'shifted based on the source.  If fewer values are given than '
                't indices, the last two value given imply a stride for the '
                'remainder.',
            'type': 'array',
            'items': {'type': 'number'},
            'minItems': 1,
        },
        'xyValues': {
            'description':
                'The numerical xy position of the different xy indices of the '
                'source.  If only one value is specified, other indices are '
                'shifted based on the source.  If fewer values are given than '
                'xy indices, the last two value given imply a stride for the '
                'remainder.',
            'type': 'array',
            'items': {'type': 'number'},
            'minItems': 1,
        },
        'cValues': {
            'description':
                'The numerical c position of the different c indices of the '
                'source.  If only one value is specified, other indices are '
                'shifted based on the source.  If fewer values are given than '
                'c indices, the last two value given imply a stride for the '
                'remainder.',
            'type': 'array',
            'items': {'type': 'number'},
            'minItems': 1,
        },
        'frameValues': {
            'description':
                'The numerical frame position of the different frame indices '
                'of the source.  If only one value is specified, other '
                'indices are shifted based on the source.  If fewer values '
                'are given than frame indices, the last two value given imply '
                'a stride for the remainder.',
            'type': 'array',
            'items': {'type': 'number'},
            'minItems': 1,
        },
        'channel': {
            'description':
                'A channel name to correspond with the main image.  Ignored '
                'if c, cValues, or channels is specified.',
            'type': 'string',
        },
        'channels': {
            'description':
                'A list of channel names used to correspond channels in this '
                'source with the main image.  Ignored if c or cValues is '
                'specified.',
            'type': 'array',
            'items': {'type': 'string'},
            'minItems': 1,
        },
        'zStep': {
            'description':
                'Step value for multiple files included via pathPattern.  '
                'Applies to z or zValues',
            'type': 'integer',
            'exclusiveMinimum': 0,
        },
        'tStep': {
            'description':
                'Step value for multiple files included via pathPattern.  '
                'Applies to t or tValues',
            'type': 'integer',
            'exclusiveMinimum': 0,
        },
        'xyStep': {
            'description':
                'Step value for multiple files included via pathPattern.  '
                'Applies to x or xyValues',
            'type': 'integer',
            'exclusiveMinimum': 0,
        },
        'xStep': {
            'description':
                'Step value for multiple files included via pathPattern.  '
                'Applies to c or cValues',
            'type': 'integer',
            'exclusiveMinimum': 0,
        },
        'framesAsAxes': {
            'description':
                'An object with keys as axes and values as strides to '
                'interpret the source frames.  This overrides the internal '
                'metadata for frames.',
            'type': 'object',
            'patternProperties': {
                '^(c|t|z|xy)$': {
                    'type': 'integer',
                    'exclusiveMinimum': 0,
                }
            },
            'additionalProperties': False,
        },
        'position': {
            'type': 'object',
            'additionalProperties': False,
            'description':
                'The image can be translated with x, y offset, apply an '
                'affine transform, and scaled.  If only part of the source is '
                'desired, a crop can be applied before the transformation.',
            'properties': {
                'x': {'type': 'number'},
                'y': {'type': 'number'},
                'crop': {
                    'description':
                        'Crop the source before applying a '
                        'position transform',
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'left': {'type': 'integer'},
                        'top': {'type': 'integer'},
                        'right': {'type': 'integer'},
                        'bottom': {'type': 'integer'},
                    },
                    # TODO: Add polygon option
                    # TODO: Add postTransform option
                },
                'scale': {
                    'description':
                        'Values less than 1 will downsample the source.  '
                        'Values greater than 1 will upsample it.',
                    'type': 'number',
                    'exclusiveMinimum': 0,
                },
                's11': {'type': 'number'},
                's12': {'type': 'number'},
                's21': {'type': 'number'},
                's22': {'type': 'number'},
            },
        },
        'frames': {
            'description': 'List of frames to use from source',
            'type': 'array',
            'items': {'type': 'integer'},
        },
        'style': {'type': 'object'},
        'params': {
            'description':
                'Additional parameters to pass to the base tile source',
            'type': 'object',
        },
    },
    'required': [
        'path',
    ],
}

MultiSourceSchema = {
    '$schema': 'http://json-schema.org/schema#',
    'type': 'object',
    'additionalProperties': False,
    'properties': {
        'name': {'type': 'string'},
        'description': {'type': 'string'},
        'width': {'type': 'integer', 'exclusiveMinimum': 0},
        'height': {'type': 'integer', 'exclusiveMinimum': 0},
        'tileWidth': {'type': 'integer', 'exclusiveMinimum': 0},
        'tileHeight': {'type': 'integer', 'exclusiveMinimum': 0},
        'channels': {
            'description': 'A list of channel names',
            'type': 'array',
            'items': {'type': 'string'},
            'minItems': 1,
        },
        'scale': {
            'type': 'object',
            'additionalProperties': False,
            'properties': {
                'mm_x': {'type': 'number', 'exclusiveMinimum': 0},
                'mm_y': {'type': 'number', 'exclusiveMinimum': 0},
                'magnification': {'type': 'integer', 'exclusiveMinimum': 0},
            },
        },
        # 'projection': {
        #     'description': 'If specified, sources are treated as '
        #                    'non-geospatial and then this projection is added',
        #     'type': 'string',
        # },
        # corner points in the projection?
        'backgroundColor': {
            'description': 'A list of background color values (fill color) in '
                           'the same scale and band order as the first tile '
                           'source (e.g., white might be [255, 255, 255] for '
                           'a three channel image).',
            'type': 'array',
            'items': {'type': 'number'},
        },
        'basePath': {
            'decription':
                'A relative path that is used as a base for all paths in '
                'sources.  Defaults to the directory of the main file.',
            'type': 'string',
        },
        'uniformSources': {
            'description':
                'If true and the first two sources are similar in frame '
                'layout and size, assume all sources are so similar',
            'type': 'boolean',
        },
        'sources': {
            'type': 'array',
            'items': SourceEntrySchema
        },
        # TODO: add merge method for cases where the are pixels from multiple
        # sources in the same output location.
    },
    'required': [
        'sources',
    ],
}


class MultiFileTileSource(FileTileSource, metaclass=LruCacheMetaclass):
    """
    Provides tile access to a composite of other tile sources.
    """

    cacheName = 'tilesource'
    name = 'multi'
    extensions = {
        None: SourcePriority.MEDIUM,
        'json': SourcePriority.PREFERRED,
        'yaml': SourcePriority.PREFERRED,
        'yml': SourcePriority.PREFERRED,
    }
    mimeTypes = {
        None: SourcePriority.FALLBACK,
        'application/json': SourcePriority.PREFERRED,
        'application/yaml': SourcePriority.PREFERRED,
    }

    _minTileSize = 64
    _maxTileSize = 4096
    _defaultTileSize = 256
    _maxOpenHandles = 6

    _validator = jsonschema.Draft6Validator(MultiSourceSchema)

    def __init__(self, path, **kwargs):
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: a filesystem path for the tile source.
        """
        super().__init__(path, **kwargs)

        self._largeImagePath = self._getLargeImagePath()
        if not os.path.isfile(self._largeImagePath):
            try:
                possibleYaml = self._largeImagePath.split('multi://', 1)[-1]
                self._info = yaml.safe_load(possibleYaml)
                self._validator.validate(self._info)
                self._basePath = Path('.')
            except Exception:
                raise TileSourceFileNotFoundError(self._largeImagePath) from None
        else:
            try:
                with builtins.open(self._largeImagePath) as fptr:
                    start = fptr.read(1024).strip()
                    if start[:1] not in ('{', '#', '-') and (start[:1] < 'a' or start[:1] > 'z'):
                        raise TileSourceError('File cannot be opened via multi-source reader.')
                    fptr.seek(0)
                    try:
                        import orjson
                        self._info = orjson.loads(fptr.read())
                    except Exception:
                        fptr.seek(0)
                        self._info = yaml.safe_load(fptr)
            except (json.JSONDecodeError, yaml.YAMLError, UnicodeDecodeError):
                raise TileSourceError('File cannot be opened via multi-source reader.')
            self._validator.validate(self._info)
            self._basePath = Path(self._largeImagePath).parent
        self._basePath /= Path(self._info.get('basePath', '.'))
        self._collectFrames()

    def _resolvePathPatterns(self, sources, source):
        """
        Given a source resolve pathPattern entries to specific paths.
        Ensure that all paths exist.

        :param sources: a list to append found sources to.
        :param source: the specific source record with a pathPattern to
            resolve.
        """
        kept = []
        pattern = re.compile(source['pathPattern'])
        basedir = self._basePath / source['path']
        if (self._basePath.name == Path(self._largeImagePath).name and
                (self._basePath.parent / source['path']).is_dir()):
            basedir = self._basePath.parent / source['path']
        basedir = basedir.resolve()
        for entry in basedir.iterdir():
            match = pattern.search(entry.name)
            if match:
                if entry.is_file():
                    kept.append((entry.name, entry, match))
                elif entry.is_dir() and (entry / entry.name).is_file():
                    kept.append((entry.name, entry / entry.name, match))
        for idx, (_, entry, match) in enumerate(sorted(kept)):
            subsource = copy.deepcopy(source)
            # Use named match groups to augment source values.
            for k, v in match.groupdict().items():
                if v.isdigit():
                    v = int(v)
                    if k.endswith('1'):
                        v -= 1
                if '.' in k:
                    subsource.setdefault(k.split('.', 1)[0], {})[k.split('.', 1)[1]] = v
                else:
                    subsource[k] = v
            subsource['path'] = entry
            for axis in ['z', 't', 'xy', 'c']:
                stepKey = '%sStep' % axis
                valuesKey = '%sValues' % axis
                if stepKey in source:
                    if axis in source or valuesKey not in source:
                        subsource[axis] = subsource.get(axis, 0) + idx * source[stepKey]
                    else:
                        subsource[valuesKey] = [
                            val + idx * source[stepKey] for val in subsource[valuesKey]]
            del subsource['pathPattern']
            sources.append(subsource)

    def _resolveSourcePath(self, sources, source):
        """
        Given a single source without a pathPattern, resolve to a specific
        path, ensuring that it exists.

        :param sources: a list to append found sources to.
        :param source: the specific source record to resolve.
        """
        source = copy.deepcopy(source)
        if source['path'] != '__none__':
            sourcePath = Path(source['path'])
            source['path'] = self._basePath / sourcePath
            if not source['path'].is_file():
                altpath = self._basePath.parent / sourcePath / sourcePath.name
                if altpath.is_file():
                    source['path'] = altpath
            if not source['path'].is_file():
                raise TileSourceFileNotFoundError(str(source['path']))
        sources.append(source)

    def _resolveFramePaths(self, sourceList):
        """
        Given a list of sources, resolve path and pathPattern entries to
        specific paths.
        Ensure that all paths exist.

        :param sourceList: a list of source entries to resolve and check.
        :returns: sourceList: a expanded and checked list of sources.
        """
        # we want to work with both _basePath / <path> and
        # _basePath / .. / <path> / <name> to be compatible with Girder
        # resource layouts.
        sources = []
        for source in sourceList:
            if source.get('pathPattern'):
                self._resolvePathPatterns(sources, source)
            else:
                self._resolveSourcePath(sources, source)
        return sources

    def _sourceBoundingBox(self, source, width, height):
        """
        Given a source with a possible transform and an image width and height,
        compute the bounding box for the source.  If a crop is used, it is
        included in the results.  If a non-identify transform is used, both it
        and its inverse are included in the results.

        :param source: a dictionary that may have a position record.
        :param width: the width of the source to transform.
        :param height: the height of the source to transform.
        :returns: a dictionary with left, top, right, bottom of the bounding
            box in the final coordinate space.
        """
        pos = source.get('position')
        bbox = {'left': 0, 'top': 0, 'right': width, 'bottom': height}
        if not pos:
            return bbox
        x0, y0, x1, y1 = 0, 0, width, height
        if 'crop' in pos:
            x0 = min(max(pos['crop'].get('left', x0), 0), width)
            y0 = min(max(pos['crop'].get('top', y0), 0), height)
            x1 = min(max(pos['crop'].get('right', x1), x0), width)
            y1 = min(max(pos['crop'].get('bottom', y1), y0), height)
            bbox['crop'] = {'left': x0, 'top': y0, 'right': x1, 'bottom': y1}
        corners = numpy.array([[x0, y0, 1], [x1, y0, 1], [x0, y1, 1], [x1, y1, 1]])
        m = numpy.identity(3)
        m[0][0] = pos.get('s11', 1) * pos.get('scale', 1)
        m[0][1] = pos.get('s12', 0) * pos.get('scale', 1)
        m[0][2] = pos.get('x', 0)
        m[1][0] = pos.get('s21', 0) * pos.get('scale', 1)
        m[1][1] = pos.get('s22', 1) * pos.get('scale', 1)
        m[1][2] = pos.get('y', 0)
        if not numpy.array_equal(m, numpy.identity(3)):
            bbox['transform'] = m
            try:
                bbox['inverse'] = numpy.linalg.inv(m)
            except numpy.linalg.LinAlgError:
                raise TileSourceError('The position for a source is not invertable (%r)', pos)
        transcorners = numpy.dot(m, corners.T)
        bbox['left'] = min(transcorners[0])
        bbox['top'] = min(transcorners[1])
        bbox['right'] = max(transcorners[0])
        bbox['bottom'] = max(transcorners[1])
        return bbox

    def _axisKey(self, source, value, key):
        """
        Get the value for a particular axis given the source specification.

        :param source: a source specification.
        :param value: a default or initial value.
        :param key: the axis key.  One of frame, c, z, t, xy.
        :returns: the axis key (an integer).
        """
        if source.get('%sSet' % key) is not None:
            return source.get('%sSet' % key)
        vals = source.get('%sValues' % key) or []
        if not vals:
            axisKey = value + source.get(key, 0)
        elif len(vals) == 1:
            axisKey = vals[0] + value + source.get(key, 0)
        elif value < len(vals):
            axisKey = vals[value] + source.get(key, 0)
        else:
            axisKey = (vals[len(vals) - 1] + (vals[len(vals) - 1] - vals[len(vals) - 2]) *
                       (value - len(vals) + source.get(key, 0)))
        return axisKey

    def _adjustFramesAsAxes(self, frames, idx, framesAsAxes):
        """
        Given a dictionary of axes and strides, relabel the indices in a frame
        as if it was based on those strides.

        :param frames: a list of frames from the tile source.
        :param idx: 0-based index of the frame to adjust.
        :param framesAsAxes: dictionary of axes and strides to apply.
        :returns: the adjusted frame record.
        """
        axisRange = {}
        slen = len(frames)
        check = 1
        for stride, axis in sorted([[v, k] for k, v in framesAsAxes.items()], reverse=True):
            axisRange[axis] = slen // stride
            slen = stride
            check *= axisRange[axis]
        if check != len(frames) and not hasattr(self, '_warnedAdjustFramesAsAxes'):
            self.logger.warning('framesAsAxes strides do not use all frames.')
            self._warnedAdjustFramesAsAxes = True
        frame = frames[idx].copy()
        for axis in ['c', 'z', 't', 'xy']:
            frame.pop('Index' + axis.upper(), None)
        for axis, stride in framesAsAxes.items():
            frame['Index' + axis.upper()] = (idx // stride) % axisRange[axis]
        return frame

    def _addSourceToFrames(self, tsMeta, source, sourceIdx, frameDict):
        """
        Add a source to the all appropriate frames.

        :param tsMeta: metadata from the source or from a matching uniform
            source.
        :param source: the source record.
        :param sourceIdx: the index of the source.
        :param frameDict: a dictionary to log the found frames.
        """
        frames = tsMeta.get('frames', [{'Frame': 0, 'Index': 0}])
        # Channel names
        channels = tsMeta.get('channels', [])
        if source.get('channels'):
            channels[:len(source['channels'])] = source['channels']
        elif source.get('channel'):
            channels[:1] = [source['channel']]
        if len(channels) > len(self._channels):
            self._channels += channels[len(self._channels):]
        if not any(key in source for key in {
                'frame', 'c', 'z', 't', 'xy',
                'frameValues', 'cValues', 'zValues', 'tValues', 'xyValues'}):
            source = source.copy()
            if len(frameDict['byFrame']):
                source['frame'] = max(frameDict['byFrame'].keys()) + 1
            if len(frameDict['byAxes']):
                source['z'] = max(aKey[1] for aKey in frameDict['byAxes']) + 1
        for frameIdx, frame in enumerate(frames):
            if 'frames' in source and frameIdx not in source['frames']:
                continue
            if source.get('framesAsAxes'):
                frame = self._adjustFramesAsAxes(frames, frameIdx, source.get('framesAsAxes'))
            fKey = self._axisKey(source, frameIdx, 'frame')
            cIdx = frame.get('IndexC', 0)
            zIdx = frame.get('IndexZ', 0)
            tIdx = frame.get('IndexT', 0)
            xyIdx = frame.get('IndexXY', 0)
            aKey = (self._axisKey(source, cIdx, 'c'),
                    self._axisKey(source, zIdx, 'z'),
                    self._axisKey(source, tIdx, 't'),
                    self._axisKey(source, xyIdx, 'xy'))
            channel = channels[cIdx] if cIdx < len(channels) else None
            if channel and channel not in self._channels and (
                    'channel' in source or 'channels' in source):
                self._channels.append(channel)
            if (channel and channel in self._channels and
                    'c' not in source and 'cValues' not in source):
                aKey = (self._channels.index(channel), aKey[1], aKey[2], aKey[3])
            kwargs = source.get('params', {}).copy()
            if 'style' in source:
                kwargs['style'] = source['style']
            kwargs.pop('frame', None)
            kwargs.pop('encoding', None)
            frameDict['byFrame'].setdefault(fKey, [])
            frameDict['byFrame'][fKey].append({
                'sourcenum': sourceIdx,
                'frame': frameIdx,
                'kwargs': kwargs,
            })
            frameDict['axesAllowed'] = (frameDict['axesAllowed'] and (
                len(frames) <= 1 or 'IndexRange' in tsMeta)) or aKey != (0, 0, 0, 0)
            frameDict['byAxes'].setdefault(aKey, [])
            frameDict['byAxes'][aKey].append({
                'sourcenum': sourceIdx,
                'frame': frameIdx,
                'kwargs': kwargs,
            })

    def _frameDictToFrames(self, frameDict):
        """
        Given a frame dictionary, populate a frame list.

        :param frameDict: a dictionary with known frames stored in byAxes if
            axesAllowed is True or byFrame if it is False.
        :returns: a list of frames with enough information to generate them.
        """
        frames = []
        if not frameDict['axesAllowed']:
            frameCount = max(frameDict['byFrame']) + 1
            for frameIdx in range(frameCount):
                frame = {'sources': frameDict['byFrame'].get(frameIdx, [])}
                frames.append(frame)
        else:
            axesCount = [max(aKey[idx] for aKey in frameDict['byAxes']) + 1 for idx in range(4)]
            for xy, t, z, c in itertools.product(
                    range(axesCount[3]), range(axesCount[2]),
                    range(axesCount[1]), range(axesCount[0])):
                aKey = (c, z, t, xy)
                frame = {
                    'sources': frameDict['byAxes'].get(aKey, []),
                }
                if axesCount[0] > 1:
                    frame['IndexC'] = c
                if axesCount[1] > 1:
                    frame['IndexZ'] = z
                if axesCount[2] > 1:
                    frame['IndexT'] = t
                if axesCount[3] > 1:
                    frame['IndexXY'] = xy
                frames.append(frame)
        return frames

    def _collectFrames(self, checkAll=False):
        """
        Using the specification in _info, enumerate the source files and open
        at least the first two of them to build up the frame specifications.

        :param checkAll: if True, open all source files.
        """
        self._sources = sources = self._resolveFramePaths(self._info['sources'])
        self.logger.debug('Sources: %r', sources)

        frameDict = {'byFrame': {}, 'byAxes': {}, 'axesAllowed': True}
        numChecked = 0

        self._associatedImages = {}
        self._sourcePaths = {}
        self._channels = self._info.get('channels') or []

        absLargeImagePath = os.path.abspath(self._largeImagePath)
        computedWidth = computedHeight = 0
        self.tileWidth = self._info.get('tileWidth')
        self.tileHeight = self._info.get('tileHeight')
        self._nativeMagnification = {
            'mm_x': self._info.get('scale', {}).get('mm_x') or None,
            'mm_y': self._info.get('scale', {}).get('mm_y') or None,
            'magnification': self._info.get('scale', {}).get('magnification') or None,
        }
        # Walk through the sources, opening at least the first two, and
        # construct a frame list.  Each frame is a list of sources that affect
        # it along with the frame number from that source.
        for sourceIdx, source in enumerate(sources):
            path = source['path']
            if os.path.abspath(path) == absLargeImagePath:
                raise TileSourceError('Multi source specification is self-referential')
            if numChecked < 2 or checkAll or not self._info.get('uniformSources'):
                # need kwargs of frame, style?
                ts = self._openSource(source)
                self.tileWidth = self.tileWidth or ts.tileWidth
                self.tileHeight = self.tileHeight or ts.tileHeight
                if not numChecked:
                    tsMag = ts.getNativeMagnification()
                    for key in self._nativeMagnification:
                        self._nativeMagnification[key] = (
                            self._nativeMagnification[key] or tsMag.get(key))
                numChecked += 1
                tsMeta = ts.getMetadata()
                if 'bands' in tsMeta:
                    if not hasattr(self, '_bands'):
                        self._bands = {}
                    self._bands.update(tsMeta['bands'])
            bbox = self._sourceBoundingBox(source, tsMeta['sizeX'], tsMeta['sizeY'])
            computedWidth = max(computedWidth, int(math.ceil(bbox['right'])))
            computedHeight = max(computedHeight, int(math.ceil(bbox['bottom'])))
            # Record this path
            if path not in self._sourcePaths:
                self._sourcePaths[path] = {
                    'frames': set(),
                    'sourcenum': set(),
                }
                # collect associated images
                for basekey in ts.getAssociatedImagesList():
                    key = basekey
                    keyidx = 0
                    while key in self._associatedImages:
                        keyidx += 1
                        key = '%s-%d' % (basekey, keyidx)
                    self._associatedImages[key] = {
                        'sourcenum': sourceIdx,
                        'key': key
                    }
            source['metadata'] = tsMeta
            source['bbox'] = bbox
            self._sourcePaths[path]['sourcenum'].add(sourceIdx)
            # process metadata to determine what frames are used, etc.
            self._addSourceToFrames(tsMeta, source, sourceIdx, frameDict)
        # Check frameDict and create frame record
        self._frames = self._frameDictToFrames(frameDict)
        self.tileWidth = min(max(self.tileWidth, self._minTileSize), self._maxTileSize)
        self.tileHeight = min(max(self.tileHeight, self._minTileSize), self._maxTileSize)
        self.sizeX = self._info.get('width') or computedWidth
        self.sizeY = self._info.get('height') or computedHeight
        self.levels = int(max(1, math.ceil(math.log(
            max(self.sizeX / self.tileWidth, self.sizeY / self.tileHeight)) / math.log(2)) + 1))

    def getNativeMagnification(self):
        """
        Get the magnification at a particular level.

        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        return self._nativeMagnification.copy()

    def _openSource(self, source, params=None):
        """
        Open a tile source, possibly using a specific source.

        :param source: a dictionary with path, params, and possibly sourceName.
        :param params: a dictionary of parameters to pass to the open call.
        :returns: a tile source.
        """
        if not len(large_image.tilesource.AvailableTileSources):
            large_image.tilesource.loadTileSources()
        if ('sourceName' not in source or
                source['sourceName'] not in large_image.tilesource.AvailableTileSources):
            openFunc = large_image.open
        else:
            openFunc = large_image.tilesource.AvailableTileSources[source['sourceName']]
        if params is None:
            params = source.get('params', {})
        return openFunc(source['path'], **params, format=format)

    def getAssociatedImage(self, imageKey, *args, **kwargs):
        """
        Return an associated image.

        :param imageKey: the key of the associated image to retrieve.
        :param kwargs: optional arguments.  Some options are width, height,
            encoding, jpegQuality, jpegSubsampling, and tiffCompression.
        :returns: imageData, imageMime: the image data and the mime type, or
            None if the associated image doesn't exist.
        """
        if imageKey not in self._associatedImages:
            return
        source = self._sources[self._associatedImages[imageKey]['sourcenum']]
        ts = self._openSource(source)
        return ts.getAssociatedImage(self._associatedImages[imageKey]['key'], *args, **kwargs)

    def getAssociatedImagesList(self):
        """
        Return a list of associated images.

        :return: the list of image keys.
        """
        return list(sorted(self._associatedImages.keys()))

    def getMetadata(self):
        """
        Return a dictionary of metadata containing levels, sizeX, sizeY,
        tileWidth, tileHeight, magnification, mm_x, mm_y, and frames.

        :returns: metadata dictionary.
        """
        result = super().getMetadata()
        if len(self._frames) > 1:
            result['frames'] = [
                {k: v for k, v in frame.items() if k.startswith('Index')}
                for frame in self._frames]
            self._addMetadataFrameInformation(result, self._channels)
        if hasattr(self, '_bands'):
            result['bands'] = self._bands.copy()
        return result

    def getInternalMetadata(self, **kwargs):
        """
        Return additional known metadata about the tile source.  Data returned
        from this method is not guaranteed to be in any particular format or
        have specific values.

        :returns: a dictionary of data or None.
        """
        result = {
            'frames': copy.deepcopy(self._frames),
            'sources': copy.deepcopy(self._sources),
            'sourceFiles': [],
        }
        for path in self._sourcePaths.values():
            source = self._sources[min(path['sourcenum'])]
            ts = self._openSource(source)
            result['sourceFiles'].append({
                'path': source['path'],
                'internal': ts.getInternalMetadata(),
            })
        return result

    def _mergeTiles(self, base, tile, x, y):
        """
        Add a tile to an existing tile.  The existing tile is expanded as
        needed, and the number of channels will always be the greater of the
        two.

        :param base: numpy array base tile.  May be None.  May be modified.
        :param tile: numpy tile to add.
        :param x: location to add the tile.
        :param y: location to add the tile.
        :returns: a numpy tile.
        """
        # Replace non blank pixels, aggregating opacity appropriately
        x = int(round(x))
        y = int(round(y))
        if base is None and not x and not y:
            return tile
        if base is None:
            base = numpy.zeros((0, 0, tile.shape[2]), dtype=tile.dtype)
        base, tile = _makeSameChannelDepth(base, tile)
        if base.shape[0] < tile.shape[0] + y:
            vfill = numpy.zeros(
                (tile.shape[0] + y - base.shape[0], base.shape[1], base.shape[2]),
                dtype=base.dtype)
            if base.shape[2] == 2 or base.shape[2] == 4:
                vfill[:, :, -1] = 1
            base = numpy.vstack((base, vfill))
        if base.shape[1] < tile.shape[1] + x:
            hfill = numpy.zeros(
                (base.shape[0], tile.shape[1] + x - base.shape[1], base.shape[2]),
                dtype=base.dtype)
            if base.shape[2] == 2 or base.shape[2] == 4:
                hfill[:, :, -1] = 1
            base = numpy.hstack((base, hfill))
        base[y:y + tile.shape[0], x:x + tile.shape[1], :] = tile
        return base

    def _addSourceToTile(self, tile, sourceEntry, corners, scale):
        """
        Add a source to the current tile.

        :param tile: a numpy array with the tile, or None if there is no data
            yet.
        :param sourceEntry: the current record from the sourceList.  This
            contains the sourcenum, kwargs to apply when opening the source,
            and the frame within the source to fetch.
        :param corners: the four corners of the tile in the main image space
            coordinates.
        :param scale: power of 2 scale of the output; this is tne number of
            pixels that are conceptually aggregated from the source for one
            output pixel.
        :returns: a numpy array of the tile.
        """
        source = self._sources[sourceEntry['sourcenum']]
        ts = self._openSource(source, sourceEntry['kwargs'])
        # If tile is outside of bounding box, skip it
        bbox = source['bbox']
        if (corners[2][0] <= bbox['left'] or corners[0][0] >= bbox['right'] or
                corners[2][1] <= bbox['top'] or corners[0][1] >= bbox['bottom']):
            return tile
        transform = bbox.get('transform')
        srccorners = (
            list(numpy.dot(bbox['inverse'], numpy.array(corners).T).T)
            if transform is not None else corners)
        x = y = 0
        # If there is no transform or the diagonals are positive and there is
        #   no sheer, use getRegion with an appropriate size (be wary of edges)
        if (transform is None or
                transform[0][0] > 0 and transform[0][1] == 0 and
                transform[1][0] == 0 and transform[1][1] > 0):
            scaleX = transform[0][0] if transform is not None else 1
            scaleY = transform[1][1] if transform is not None else 1
            region = {
                'left': srccorners[0][0], 'top': srccorners[0][1],
                'right': srccorners[2][0], 'bottom': srccorners[2][1]
            }
            output = {
                'maxWidth': (corners[2][0] - corners[0][0]) // scale,
                'maxHeight': (corners[2][1] - corners[0][1]) // scale,
            }
            if region['left'] < 0:
                x -= region['left'] * scaleX // scale
                output['maxWidth'] += int(region['left'] * scaleX // scale)
                region['left'] = 0
            if region['top'] < 0:
                y -= region['top'] * scaleY // scale
                output['maxHeight'] += int(region['top'] * scaleY // scale)
                region['top'] = 0
            if region['right'] > source['metadata']['sizeX']:
                output['maxWidth'] -= int(
                    (region['right'] - source['metadata']['sizeX']) * scaleX // scale)
                region['right'] = source['metadata']['sizeX']
            if region['bottom'] > source['metadata']['sizeY']:
                output['maxHeight'] -= int(
                    (region['bottom'] - source['metadata']['sizeY']) * scaleY // scale)
                region['bottom'] = source['metadata']['sizeY']
            for key in region:
                region[key] = int(round(region[key]))
            self.logger.debug('getRegion: ts: %r, region: %r, output: %r', ts, region, output)
            sourceTile, _ = ts.getRegion(
                region=region, output=output, frame=sourceEntry.get('frame', 0),
                format=TILE_FORMAT_NUMPY)
        # Otherwise, get an area twice as big as needed and use
        #  scipy.ndimage.affine_transform to transform it
        else:
            # TODO
            raise TileSourceError('Not implemented')
        # Crop
        # TODO
        tile = self._mergeTiles(tile, sourceTile, x, y)
        return tile

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False, **kwargs):
        frame = self._getFrame(**kwargs)
        self._xyzInRange(x, y, z, frame, len(self._frames) if hasattr(self, '_frames') else None)
        scale = 2 ** (self.levels - 1 - z)
        corners = [[
            x * self.tileWidth * scale,
            y * self.tileHeight * scale,
            1,
        ], [
            min((x + 1) * self.tileWidth * scale, self.sizeX),
            y * self.tileHeight * scale,
            1,
        ], [
            min((x + 1) * self.tileWidth * scale, self.sizeX),
            min((y + 1) * self.tileHeight * scale, self.sizeY),
            1,
        ], [
            x * self.tileWidth * scale,
            min((y + 1) * self.tileHeight * scale, self.sizeY),
            1,
        ]]
        sourceList = self._frames[frame]['sources']
        tile = None
        # If the first source does not completely cover the output tile or uses
        # a transformation, create a tile that is the desired size and fill it
        # with the background color.
        fill = not len(sourceList)
        if not fill:
            firstsource = self._sources[sourceList[0]['sourcenum']]
            fill = 'transform' in firstsource['bbox'] or any(
                cx < firstsource['bbox']['left'] or
                cx > firstsource['bbox']['right'] or
                cy < firstsource['bbox']['top'] or
                cy > firstsource['bbox']['bottom'] for cx, cy, _ in corners)
        if fill:
            colors = self._info.get('backgroundColor')
            if colors:
                tile = numpy.full((self.tileHeight, self.tileWidth, len(colors)), colors)
        # Add each source to the tile
        for sourceEntry in sourceList:
            tile = self._addSourceToTile(tile, sourceEntry, corners, scale)
        if tile is None:
            # TODO number of channels?
            colors = self._info.get('backgroundColor', [0])
            if colors:
                tile = numpy.full((self.tileHeight, self.tileWidth, len(colors)), colors)
        # We should always have a tile
        return self._outputTile(tile, TILE_FORMAT_NUMPY, x, y, z,
                                pilImageAllowed, numpyAllowed, **kwargs)


def open(*args, **kwargs):
    """
    Create an instance of the module class.
    """
    return MultiFileTileSource(*args, **kwargs)


def canRead(*args, **kwargs):
    """
    Check if an input can be read by the module class.
    """
    return MultiFileTileSource.canRead(*args, **kwargs)
