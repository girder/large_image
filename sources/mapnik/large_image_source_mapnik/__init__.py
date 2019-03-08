# -*- coding: utf-8 -*-

#############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#############################################################################

# There is an issue with some of the wheels with pyvips and mapnik where if
# both are to be imported, pyvips must be imported first.  To handle this,
# even though we don't need pyvips, try to import it before mapnik.
import os
try:
    # Because of its use of gobject, pyvips should be invoked without concurrency
    os.environ['VIPS_CONCURRENCY'] = '1'
    import pyvips  # noqa
except ImportError:
    pass
import json
import mapnik
import math
import PIL.Image
import palettable
import pyproj
import six
import struct
import threading
from operator import attrgetter
from osgeo import gdal
from osgeo import osr
from pkg_resources import DistributionNotFound, get_distribution

from large_image import config
from large_image.cache_util import LruCacheMetaclass, methodcache, strhash
from large_image.constants import SourcePriority, TileInputUnits
from large_image.exceptions import TileSourceException
from large_image.tilesource import FileTileSource, TILE_FORMAT_PIL


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


TileInputUnits['projection'] = 'projection'
TileInputUnits['proj'] = 'projection'
TileInputUnits['wgs84'] = 'proj4:EPSG:4326'
TileInputUnits['4326'] = 'proj4:EPSG:4326'


@six.add_metaclass(LruCacheMetaclass)
class MapnikFileTileSource(FileTileSource):
    """
    Provides tile access to geospatial files.
    """
    cacheName = 'tilesource'
    name = 'mapnikfile'
    extensions = {
        None: SourcePriority.MEDIUM,
        'nc': SourcePriority.PREFERRED,  # netcdf
        'tif': SourcePriority.LOW,
        'tiff': SourcePriority.LOW,
    }
    mimeTypes = {
        None: SourcePriority.FALLBACK,
        'image/geotiff': SourcePriority.PREFERRED,
        'image/tiff': SourcePriority.LOW,
        'image/x-tiff': SourcePriority.LOW,
    }

    def __init__(self, path, projection=None, style=None, unitsPerPixel=None, **kwargs):
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: a filesystem path for the tile source.
        :param projection: None to use pixel space, otherwise a proj4
            projection string or a case-insensitive string of the form
            'EPSG:<epsg number>'.  If a string and case-insensitively prefixed
            with 'proj4:', that prefix is removed.  For instance,
            'proj4:EPSG:3857', 'PROJ4:+init=epsg:3857', and '+init=epsg:3857',
            and 'EPSG:3857' are all equivilant.
        :param style: if None, use the default style for the file.  Otherwise,
            this is a string with a json-encoded dictionary.  The style is
            ignored if it does not contain 'band' or 'bands'.  The style can
            contain the following keys:
                band: either -1 for the default band(s), a 1-based value for
                    the band to use for styling, or a string that matches the
                    interpretation of the band ('red', 'green', 'blue', gray',
                    etc.).
                min: the value of the band to map to the first palette value.
                    Defaults to 0.  'auto' to use 0 if the reported minimum and
                    maximum of the band are between [0, 255] or use the
                    reported minimum otherwise.  'min' or 'max' to always uses
                    the reported minimum or maximum.
                max: the value of the band to map to the last palette value.
                    Defaults to 255.  'auto' to use 0 if the reported minimum
                    and maximum of the band are between [0, 255] or use the
                    reported maximum otherwise.  'min' or 'max' to always uses
                    the reported minimum or maximum.
                scheme: one of the mapnik.COLORIZER_xxx values.  Case
                    insensitive.  Possible values are at least 'discrete',
                    'linear', and 'exact'.  If palette is unspecified and the
                    band was specified as a string, this defaults to 'linear'.
                    Otherwise it defaults to 'discrete'.
                palette: either a list of two or more color strings, a string
                    with a dotted class name from the python palettable
                    package, or 'colortable' to use the band's color table
                    (palette).  Color strings must be parsable by mapnik's
                    Color class.  Many css strings work.  If scheme is
                    unspecified and the band is one of 'red', 'green', 'blue',
                    gray', or 'alpha', this defaults to an appropriate band
                    pair.  Otherwise, this defaults to the band's color table
                    (palette) if it has one and 'cmocean.diverging.Curl_10' if
                    it does not.
                nodata: the value to use for missing data.  'auto' to use the
                    band reported value, if any.  null or unset to not use a
                    nodata value.
                composite: this is a string containing one of the mapnik
                    CompositeOp properties.  It defaults to 'lighten'.
            Alternately, the style object can contain a single key of 'bands',
            which has a value which is a list of style dictionaries as above,
            excepting that each must have a band that is not -1.  Bands are
            composited in the order listed.
        :param unitsPerPixel: The size of a pixel at the 0 tile size.  Ignored
            if the projection is None.  For projections, None uses the default,
            which is the distance between (-180,0) and (180,0) in EPSG:4326
            converted to the projection divided by the tile size.  Proj4
            projections that are not latlong (is_geographic is False) must
            specify unitsPerPixel.
        """
        super(MapnikFileTileSource, self).__init__(path, **kwargs)
        self._bounds = {}
        self._path = self._getLargeImagePath()
        self.dataset = gdal.Open(self._path)
        self.tileSize = 256
        self.tileWidth = self.tileSize
        self.tileHeight = self.tileSize
        if projection and projection.lower().startswith('epsg:'):
            projection = '+init=' + projection.lower()
        if projection and not isinstance(projection, six.binary_type):
            projection = projection.encode('utf8')
        self.projection = projection
        if style:
            try:
                self.style = json.loads(style)
                if not isinstance(self.style, dict):
                    raise TypeError
            except TypeError:
                raise TileSourceException('Style is not a valid json object.')

        try:
            self.sourceSizeX = self.sizeX = self.dataset.RasterXSize
            self.sourceSizeY = self.sizeY = self.dataset.RasterYSize
        except AttributeError:
            raise TileSourceException('File cannot be opened via Mapnik.')
        is_netcdf = self._checkNetCDF()
        try:
            scale = self.getPixelSizeInMeters()
        except RuntimeError:
            raise TileSourceException('File cannot be opened via Mapnik.')
        if not scale and not is_netcdf:
            raise TileSourceException(
                'File does not have a projected scale, so will not be '
                'opened via Mapnik.')
        self.sourceLevels = self.levels = int(max(0, math.ceil(max(
            math.log(float(self.sizeX) / self.tileWidth),
            math.log(float(self.sizeY) / self.tileHeight)) / math.log(2))) + 1)
        if self.projection:
            self._initWithProjection(unitsPerPixel)
        self._getTileLock = threading.Lock()

    def _checkNetCDF(self):
        """
        Check if this file is a netCDF file.  If so, get some metadata about
        available datasets.

        This assumes things about the projection that may not be true for all
        netCDF files.  It could also be extended to get better data about
        time bounds and other series data and to prevent selecting subdatasets
        that are not spatially appropriate.
        """
        if not self.dataset or not self.dataset.GetDriver():
            return False
        if self.dataset.GetDriver().ShortName != 'netCDF':
            return False
        datasets = {}
        for name, desc in self.dataset.GetSubDatasets():
            parts = desc.split(None, 2)
            dataset = {
                'name': name,
                'desc': desc,
                'dim': [int(val) for val in parts[0].strip('[]').split('x')],
                'key': parts[1],
                'format': parts[2],
            }
            dataset['values'] = six.moves.reduce(lambda x, y: x * y, dataset['dim'])
            datasets[dataset['key']] = dataset
        if not len(datasets) and (not self.dataset.RasterCount or self.dataset.GetProjection()):
            return False
        self._netcdf = {
            'datasets': datasets,
            'metadata': self.dataset.GetMetadata_Dict()
        }
        if not len(datasets):
            try:
                self.getBounds('+init=epsg:3857')
            except RuntimeError:
                self._bounds.clear()
                del self._netcdf
                return False
        if not self.dataset.RasterCount:
            self._netcdf['default'] = sorted([(
                not ds['key'].endswith('_bnds'),
                'character' not in ds['format'],
                ds['values'],
                len(ds['dim']),
                ds['dim'],
                ds['key']) for ds in six.itervalues(datasets)])[-1][-1]
            # The base netCDF file reports different dimensions than the
            # subdatasets.  For now, use the "best" subdataset's dimensions
            dataset = self._netcdf['datasets'][self._netcdf['default']]
            dataset['dataset'] = gdal.Open(dataset['name'])
            self.sourceSizeX = self.sizeX = dataset['dataset'].RasterXSize
            self.sourceSizeY = self.sizeY = dataset['dataset'].RasterYSize

            self.dataset = dataset['dataset']  # use for projection information

        if not hasattr(self, 'style'):
            self.style = {
                'band': self._netcdf['default'] + ':1' if self._netcdf.get('default') else 1,
                'scheme': 'linear',
                'palette': ['#000000', '#ffffff'],
                'min': 'min',
                'max': 'max'
            }
        return True

    def _initWithProjection(self, unitsPerPixel=None):
        """
        Initialize aspects of the class when a projection is set.
        """
        inProj = self._proj4Proj('+init=epsg:4326')
        # Since we already converted to bytes decoding is safe here
        outProj = self._proj4Proj(self.projection)
        if outProj.crs.is_geographic:
            raise TileSourceException(
                'Projection must not be geographic (it needs to use linear '
                'units, not longitude/latitude).')
        # If unitsPerPixel is not specified, the horizontal distance
        # between -180,0 and +180,0 is used.  Some projections (such as
        # stereographic) will fail in this case; they must have a
        # unitsPerPixel specified.
        if unitsPerPixel:
            self.unitsAcrossLevel0 = float(unitsPerPixel) * self.tileSize
        else:
            equator = pyproj.transform(inProj, outProj, [-180, 180], [0, 0])
            self.unitsAcrossLevel0 = abs(equator[0][1] - equator[0][0])
            if not self.unitsAcrossLevel0:
                raise TileSourceException(
                    'unitsPerPixel must be specified for this projection')
        # This was
        #   self.projectionOrigin = pyproj.transform(inProj, outProj, 0, 0)
        # but for consistency, it should probably always be (0, 0).  Whatever
        # renders the map would need the same offset as used here.
        self.projectionOrigin = (0, 0)
        # Calculate values for this projection
        self.levels = int(max(int(math.ceil(
            math.log(self.unitsAcrossLevel0 / self.getPixelSizeInMeters() / self.tileWidth) /
            math.log(2))) + 1, 1))
        # Report sizeX and sizeY as the whole world
        self.sizeX = 2 ** (self.levels - 1) * self.tileWidth
        self.sizeY = 2 ** (self.levels - 1) * self.tileHeight

    @staticmethod
    def getLRUHash(*args, **kwargs):
        return strhash(
            super(MapnikFileTileSource, MapnikFileTileSource).getLRUHash(
                *args, **kwargs),
            kwargs.get('projection', args[1] if len(args) >= 2 else None),
            kwargs.get('style', args[2] if len(args) >= 3 else None),
            kwargs.get('unitsPerPixel', args[3] if len(args) >= 4 else None))

    def getProj4String(self):
        """
        Returns proj4 string for the given dataset

        :returns: The proj4 string or None.
        """
        wkt = self.dataset.GetProjection()
        if not wkt:
            if hasattr(self, '_netcdf'):
                return '+init=epsg:4326'
            return
        proj = osr.SpatialReference()
        proj.ImportFromWkt(wkt)
        return proj.ExportToProj4()

    @staticmethod
    def interpolateMinMax(start, stop, count):
        """
        Returns interpolated values for a given
        start, stop and count

        :returns: List of interpolated values
        """
        try:
            step = (float(stop) - float(start)) / (float(count) - 1)
        except ValueError:
            raise TileSourceException(
                'Minimum and maximum values should be numbers, "auto", "min", or "max".')
        sequence = [float(start + i * step) for i in range(count)]
        return sequence

    @staticmethod
    def getHexColors(palette):
        """
        Returns list of hex colors for a given color palette

        :returns: List of colors
        """
        try:
            return attrgetter(palette)(palettable).hex_colors
        except AttributeError:
            raise TileSourceException('Palette is not a valid palettable path.')

    def getPixelSizeInMeters(self):
        """
        Get the approximate base pixel size in meters.  This is calculated as
        the average scale of the four edges in the WGS84 ellipsoid.

        :returns: the pixel size in meters or None.
        """
        bounds = self.getBounds('+init=epsg:4326')
        if not bounds:
            return
        geod = pyproj.Geod(ellps='WGS84')
        az12, az21, s1 = geod.inv(bounds['ul']['x'], bounds['ul']['y'],
                                  bounds['ur']['x'], bounds['ur']['y'])
        az12, az21, s2 = geod.inv(bounds['ur']['x'], bounds['ur']['y'],
                                  bounds['lr']['x'], bounds['lr']['y'])
        az12, az21, s3 = geod.inv(bounds['lr']['x'], bounds['lr']['y'],
                                  bounds['ll']['x'], bounds['ll']['y'])
        az12, az21, s4 = geod.inv(bounds['ll']['x'], bounds['ll']['y'],
                                  bounds['ul']['x'], bounds['ul']['y'])
        return (s1 + s2 + s3 + s4) / (self.sourceSizeX * 2 + self.sourceSizeY * 2)

    def getNativeMagnification(self):
        """
        Get the magnification at the base level.

        :return: width of a pixel in mm, height of a pixel in mm.
        """
        scale = self.getPixelSizeInMeters()
        if not scale:
            return {
                'magnification': None,
                'mm_x': None,
                'mm_y': None
            }
        return {
            'magnification': None,
            'mm_x': scale * 100,
            'mm_y': scale * 100
        }

    def getBounds(self, srs=None):
        """
        Returns bounds of the image.

        :param srs: the projection for the bounds.  None for the default.
        :returns: an object with the four corners and the projection that was
            used.  None if we don't know the original projection.
        """
        if srs not in self._bounds:
            gt = self.dataset.GetGeoTransform()
            nativeSrs = self.getProj4String()
            if not nativeSrs:
                self._bounds[srs] = None
                return
            bounds = {
                'll': {
                    'x': gt[0] + self.sourceSizeY * gt[2],
                    'y': gt[3] + self.sourceSizeY * gt[5]
                },
                'ul': {
                    'x': gt[0],
                    'y': gt[3],
                },
                'lr': {
                    'x': gt[0] + self.sourceSizeX * gt[1] + self.sourceSizeY * gt[2],
                    'y': gt[3] + self.sourceSizeX * gt[4] + self.sourceSizeY * gt[5]
                },
                'ur': {
                    'x': gt[0] + self.sourceSizeX * gt[1],
                    'y': gt[3] + self.sourceSizeX * gt[4]
                },
                'srs': nativeSrs,
            }
            # Make sure geographic coordinates do not exceed their limits
            if pyproj.Proj(nativeSrs).crs.is_geographic and srs:
                try:
                    pyproj.Proj(srs)(0, 90, errcheck=True)
                    yBound = 90.0
                except RuntimeError:
                    yBound = 89.999999
                for key in ('ll', 'ul', 'lr', 'ur'):
                    bounds[key]['y'] = max(min(bounds[key]['y'], yBound), -yBound)
            if srs and srs != nativeSrs:
                inProj = self._proj4Proj(nativeSrs)
                outProj = self._proj4Proj(srs)
                for key in ('ll', 'ul', 'lr', 'ur'):
                    pt = pyproj.transform(inProj, outProj, bounds[key]['x'], bounds[key]['y'])
                    bounds[key]['x'] = pt[0]
                    bounds[key]['y'] = pt[1]
                bounds['srs'] = srs.decode('utf8') if isinstance(srs, six.binary_type) else srs
            bounds['xmin'] = min(bounds['ll']['x'], bounds['ul']['x'],
                                 bounds['lr']['x'], bounds['ur']['x'])
            bounds['xmax'] = max(bounds['ll']['x'], bounds['ul']['x'],
                                 bounds['lr']['x'], bounds['ur']['x'])
            bounds['ymin'] = min(bounds['ll']['y'], bounds['ul']['y'],
                                 bounds['lr']['y'], bounds['ur']['y'])
            bounds['ymax'] = max(bounds['ll']['y'], bounds['ul']['y'],
                                 bounds['lr']['y'], bounds['ur']['y'])
            self._bounds[srs] = bounds
        return self._bounds[srs]

    def getBandInformation(self, dataset=None):
        if not getattr(self, '_bandInfo', None) or dataset:
            cache = not dataset
            if not dataset:
                dataset = self.dataset
            infoSet = {}
            for i in range(dataset.RasterCount):
                band = dataset.GetRasterBand(i + 1)
                info = {}
                stats = band.GetStatistics(True, True)
                # The statistics provide a min and max, so we don't fetch those
                # separately
                info.update(dict(zip(('min', 'max', 'mean', 'stdev'), stats)))
                info['nodata'] = band.GetNoDataValue()
                info['scale'] = band.GetScale()
                info['offset'] = band.GetOffset()
                info['units'] = band.GetUnitType()
                info['catgeories'] = band.GetCategoryNames()
                interp = band.GetColorInterpretation()
                info['interpretation'] = {
                    1: 'gray',
                    2: 'palette',
                    3: 'red',
                    4: 'green',
                    5: 'blue',
                    6: 'alpha',
                    7: 'hue',
                    8: 'saturation',
                    9: 'lightness',
                    10: 'cyan',
                    11: 'magenta',
                    12: 'yellow',
                    13: 'black',
                    14: 'Y',
                    15: 'Cb',
                    16: 'Cr',
                }.get(interp, interp)
                if band.GetColorTable():
                    info['colortable'] = [band.GetColorTable().GetColorEntry(pos)
                                          for pos in range(band.GetColorTable().GetCount())]
                if band.GetMaskBand():
                    info['maskband'] = band.GetMaskBand().GetBand() or None
                # Only keep values that aren't None or the empty string
                infoSet[i + 1] = {k: v for k, v in six.iteritems(info) if v not in (None, '')}
            if not cache:
                return infoSet
            self._bandInfo = infoSet
        return self._bandInfo

    def getOneBandInformation(self, band):
        if type(band) is not tuple:
            bandInfo = self.getBandInformation()[band]
        else:  # netcdf
            dataset = self._netcdf['datasets'][band[0]]
            if not dataset.get('bands'):
                if not dataset.get('dataset'):
                    dataset['dataset'] = gdal.Open(dataset['name'])
                dataset['bands'] = self.getBandInformation(dataset['dataset'])
            bandInfo = dataset['bands'][band[1]]
        return bandInfo

    def getMetadata(self):
        metadata = {
            'geospatial': bool(self.dataset.GetProjection() or hasattr(self, '_netcdf')),
            'levels': self.levels,
            'sizeX': self.sizeX,
            'sizeY': self.sizeY,
            'sourceLevels': self.sourceLevels,
            'sourceSizeX': self.sourceSizeX,
            'sourceSizeY': self.sourceSizeY,
            'tileWidth': self.tileWidth,
            'tileHeight': self.tileHeight,
            'bounds': self.getBounds(self.projection),
            'sourceBounds': self.getBounds(),
            'bands': self.getBandInformation(),
        }
        metadata.update(self.getNativeMagnification())
        if hasattr(self, '_netcdf'):
            # To ensure all band information from all subdatasets in netcdf,
            # we could do the following:
            # for key in self._netcdf['datasets']:
            #     dataset = self._netcdf['datasets'][key]
            #     if 'bands' not in dataset:
            #         gdaldataset = gdal.Open(dataset['name'])
            #         dataset['bands'] = self.getBandInformation(gdaldataset)
            #         dataset['sizeX'] = gdaldataset.RasterXSize
            #         dataset['sizeY'] = gdaldataset.RasterYSize
            metadata['netcdf'] = self._netcdf
        return metadata

    def getTileCorners(self, z, x, y):
        """
        Returns bounds of a tile for a given x,y,z index.

        :param z: tile level
        :param x: tile offset from left.
        :param y: tile offset from right
        :returns: (xmin, ymin, xmax, ymax) in the current projection or base
            pixels.
        """
        x, y = float(x), float(y)
        if self.projection:
            # Scale tile into the range [-0.5, 0.5], [-0.5, 0.5]
            xmin = -0.5 + x / 2.0 ** z
            xmax = -0.5 + (x + 1) / 2.0 ** z
            ymin = 0.5 - (y + 1) / 2.0 ** z
            ymax = 0.5 - y / 2.0 ** z
            # Convert to projection coordinates
            xmin = self.projectionOrigin[0] + xmin * self.unitsAcrossLevel0
            xmax = self.projectionOrigin[0] + xmax * self.unitsAcrossLevel0
            ymin = self.projectionOrigin[1] + ymin * self.unitsAcrossLevel0
            ymax = self.projectionOrigin[1] + ymax * self.unitsAcrossLevel0
        else:
            xmin = 2 ** (self.sourceLevels - 1 - z) * x * self.tileWidth
            ymin = 2 ** (self.sourceLevels - 1 - z) * y * self.tileHeight
            xmax = xmin + 2 ** (self.sourceLevels - 1 - z) * self.tileWidth
            ymax = ymin + 2 ** (self.sourceLevels - 1 - z) * self.tileHeight
            ymin, ymax = self.sourceSizeY - ymax, self.sourceSizeY - ymin
        return xmin, ymin, xmax, ymax

    def _colorizerFromStyle(self, style):
        """
        Add a specified style to a mapnik raster symbolizer.

        :param style: a style object.
        :returns: a mapnik raster colorizer.
        """
        try:
            scheme = style.get('scheme', 'discrete')
            mapnik_scheme = getattr(mapnik, 'COLORIZER_{}'.format(scheme.upper()))
        except AttributeError:
            mapnik_scheme = mapnik.COLORIZER_DISCRETE
            raise TileSourceException('Scheme has to be either "discrete" or "linear".')
        colorizer = mapnik.RasterColorizer(mapnik_scheme, mapnik.Color(0, 0, 0, 0))
        bandInfo = self.getOneBandInformation(style['band'])
        minimum = style.get('min', 0)
        maximum = style.get('max', 255)
        minimum = bandInfo[minimum] if minimum in ('min', 'max') else minimum
        maximum = bandInfo[maximum] if maximum in ('min', 'max') else maximum
        if minimum == 'auto':
            if not (0 <= bandInfo['min'] <= 255 and 1 <= bandInfo['max'] <= 255):
                minimum = bandInfo['min']
            else:
                minimum = 0
        if maximum == 'auto':
            if not (0 <= bandInfo['min'] <= 255 and 1 <= bandInfo['max'] <= 255):
                maximum = bandInfo['max']
            else:
                maximum = 255
        if style.get('palette') == 'colortable':
            for value, color in enumerate(bandInfo['colortable']):
                colorizer.add_stop(value, mapnik.Color(*color))
        else:
            colors = style.get('palette', 'cmocean.diverging.Curl_10')
            if not isinstance(colors, list):
                colors = self.getHexColors(colors)
            else:
                colors = [color if isinstance(color, six.binary_type) else
                          color.encode('utf8') for color in colors]
            if len(colors) < 2:
                raise TileSourceException('A palette must have at least 2 colors.')
            values = self.interpolateMinMax(minimum, maximum, len(colors))
            for value, color in sorted(zip(values, colors)):
                try:
                    colorizer.add_stop(value, mapnik.Color(color))
                except RuntimeError:
                    raise TileSourceException('Mapnik failed to parse color %r.' % color)

        return colorizer

    def _addStyleToMap(self, m, layerSrs, colorizer=None, band=-1, extent=None,
                       composite=None, nodata=None):
        """
        Add a mapik raster symbolizer to a map.

        :param m: mapnik map.
        :param layerSrs: the layer projection
        :param colorizer: a mapnik colorizer.
        :param band: an integer band number.  -1 for default.
        :param extent: the extent to use for the mapnik layer.
        :param composite: the composite operation to use.  This is one of
            mapnik.CompositeOp.xxx, typically lighten or multiply.
        :param nodata: the value to use for missing data or None to use all
            data.
        """
        styleName = 'Raster Style'
        if band != -1:
            styleName += ' ' + str(band)
        rule = mapnik.Rule()
        sym = mapnik.RasterSymbolizer()
        if colorizer is not None:
            sym.colorizer = colorizer
        rule.symbols.append(sym)
        style = mapnik.Style()
        style.rules.append(rule)
        if composite is not None:
            style.comp_op = composite
        m.append_style(styleName, style)
        lyr = mapnik.Layer('layer')
        lyr.srs = layerSrs
        gdalpath = self._path
        gdalband = band
        if hasattr(self, '_netcdf') and type(band) is tuple:
            gdalband = band[1]
            gdalpath = self._netcdf['datasets'][band[0]]['name']
        lyr.datasource = mapnik.Gdal(
            base=None, file=gdalpath, band=gdalband, extent=extent, nodata=nodata)
        lyr.styles.append(styleName)
        m.layers.append(lyr)

    def _bandNumber(self, band, exc=True):
        """
        Given a band number or interpretation name, return a validated band
        number.

        :param band: either -1, a positive integer, or the name of a band
            interpretation that is present in the tile source.
        :param exc: if True, raise an exception if no band matches.
        :returns: a validated band, either 1 or a positive integer, or None if
            no matching band and exceptions are not enabled.
        """
        if hasattr(self, '_netcdf') and (':' in str(band) or str(band).isdigit()):
            key = None
            if ':' in str(band):
                key, band = band.split(':', 1)
            if str(band).isdigit():
                band = int(band)
            else:
                band = 1
            if not key or key == 'default':
                key = self._netcdf.get('default', None)
                if key is None:
                    return band
            if key in self._netcdf['datasets']:
                return (key, band)
        bands = self.getBandInformation()
        if not isinstance(band, int):
            try:
                band = next(bandIdx for bandIdx in sorted(bands)
                            if band == bands[bandIdx]['interpretation'])
            except StopIteration:
                pass
        if hasattr(band, 'isdigit') and band.isdigit():
            band = int(band)
        if band != -1 and band not in bands:
            if exc:
                raise TileSourceException(
                    'Band has to be a positive integer, -1, or a band '
                    'interpretation found in the source.')
            return None
        return int(band)

    def addStyle(self, m, layerSrs, extent=None):
        """
        Attaches raster style option to mapnik raster layer and adds the layer
        to the mapnik map.

        :param m: mapnik map.
        :param layerSrs: the layer projection
        :param extent: the extent to use for the mapnik layer.
        """
        interpColorTable = {
            'red': ['#000000', '#ff0000'],
            'green': ['#000000', '#00ff00'],
            'blue': ['#000000', '#0000ff'],
            'gray': ['#000000', '#ffffff'],
            'alpha': ['#ffffff00', '#ffffffff'],
        }
        bands = self.getBandInformation()
        style = []
        if hasattr(self, 'style'):
            styleBands = self.style['bands'] if 'bands' in self.style else [self.style]
            for styleBand in styleBands:

                styleBand = styleBand.copy()
                styleBand['band'] = self._bandNumber(styleBand.get('band'))
                style.append(styleBand)
        if not len(style):
            for interp in ('red', 'green', 'blue', 'gray', 'palette', 'alpha'):
                band = self._bandNumber(interp, False)
                # If we don't have the requested band, or we only have alpha,
                # or this is gray or palette and we already added another band,
                # skip this interpretation.
                if (band is None or
                        (interp == 'alpha' and not len(style)) or
                        (interp in ('gray', 'palette') and len(style))):
                    continue
                if interp == 'palette':
                    style.append({'band': band, 'palette': 'colortable'})
                else:
                    style.append({
                        'band': band,
                        'palette': interpColorTable[interp],
                        'min': 'auto',
                        'max': 'auto',
                        'nodata': 'auto',
                        'scheme': 'linear',
                        'composite': 'multiply' if interp == 'alpha' else 'lighten'
                    })
        if not len(style):
            style.append({'band': -1})
        config.getConfig('logger').debug(
            'mapnik addTile specified style: %r, used style %r',
            getattr(self, 'style', None), style)
        for styleBand in style:
            if styleBand['band'] != -1:
                colorizer = self._colorizerFromStyle(styleBand)
                composite = getattr(mapnik.CompositeOp, styleBand.get('composite', 'lighten'))
                nodata = styleBand.get('nodata')
                if nodata == 'auto':
                    nodata = bands.get('nodata')
            else:
                colorizer = None
                composite = None
                nodata = None
            self._addStyleToMap(
                m, layerSrs, colorizer, styleBand['band'], extent, composite, nodata)

    @methodcache()
    def getTile(self, x, y, z, **kwargs):
        if self.projection:
            mapSrs = self.projection
            layerSrs = self.getProj4String()
            extent = None
            overscan = 0
            if not hasattr(self, '_repeatLongitude'):
                # If the original dataset is in a latitude/longitude
                # projection, and does cover more than 360 degrees in longitude
                # (with some slop), and is outside of the bounds of
                # [-180, 180], we want to render it twice, once at the
                # specified longitude and once offset to ensure that we cover
                # [-180, 180].  This is done by altering the projection's
                # prime meridian by 360 degrees.  If none of the dataset is in
                # the range of [-180, 180], this does't apply the shift either.
                self._repeatLongitude = None
                if pyproj.Proj(layerSrs).crs.is_geographic:
                    bounds = self.getBounds()
                    if bounds['xmax'] - bounds['xmin'] < 361:
                        if bounds['xmin'] < -180 and bounds['xmax'] > -180:
                            self._repeatLongitude = layerSrs + ' +pm=+360'
                        elif bounds['xmax'] > 180 and bounds['xmin'] < 180:
                            self._repeatLongitude = layerSrs + ' +pm=-360'
        else:
            mapSrs = '+proj=longlat +axis=enu'
            layerSrs = '+proj=longlat +axis=enu'
            # There appears to be a bug in some versions of mapnik/gdal when
            # requesting a tile with a bounding box that has a corner exactly
            # at (0, extentMaxY), so make a slightly larger image and crop it.
            extent = '0 0 %d %d' % (self.sourceSizeX, self.sourceSizeY)
            overscan = 1
        xmin, ymin, xmax, ymax = self.getTileCorners(z, x, y)
        if overscan:
            pw = (xmax - xmin) / self.tileWidth
            py = (ymax - ymin) / self.tileHeight
            xmin, xmax = xmin - pw * overscan, xmax + pw * overscan
            ymin, ymax = ymin - py * overscan, ymax + py * overscan
        with self._getTileLock:
            if not hasattr(self, '_mapnikMap'):
                m = mapnik.Map(
                    self.tileWidth + overscan * 2,
                    self.tileHeight + overscan * 2,
                    mapSrs)
                self.addStyle(m, layerSrs, extent)
                if getattr(self, '_repeatLongitude', None):
                    self.addStyle(m, self._repeatLongitude, extent)
                self._mapnikMap = m
            else:
                m = self._mapnikMap
            m.zoom_to_box(mapnik.Box2d(xmin, ymin, xmax, ymax))
            img = mapnik.Image(self.tileWidth + overscan * 2, self.tileHeight + overscan * 2)
            mapnik.render(m, img)
            pilimg = PIL.Image.frombytes('RGBA', (img.width(), img.height()), img.tostring())
        if overscan:
            pilimg = pilimg.crop((1, 1, pilimg.width - overscan, pilimg.height - overscan))
        return self._outputTile(pilimg, TILE_FORMAT_PIL, x, y, z, **kwargs)

    @staticmethod
    def _proj4Proj(proj):
        """
        Return a pyproj.Proj based on either a binary or unicode string.

        :param proj: a binary or unicode projection string.
        :returns: a proj4 projection object.  None if the specified projection
            cannot be created.
        """
        if isinstance(proj, six.binary_type):
            proj = proj.decode('utf8')
        if not isinstance(proj, six.text_type):
            return
        if proj.lower().startswith('proj4:'):
            proj = proj.split(':', 1)[1]
        if proj.lower().startswith('epsg:'):
            proj = '+init=' + proj.lower()
        return pyproj.Proj(proj)

    def _convertProjectionUnits(self, left, top, right, bottom, width, height,
                                units, **kwargs):
        """
        Given bound information and a units string that consists of a proj4
        projection (starts with `'proj4:'`, `'epsg:'`, `'+proj='` or is an
        enumerated value like `'wgs84'`), convert the bounds to either pixel or
        the class projection coordinates.

        :param left: the left edge (inclusive) of the region to process.
        :param top: the top edge (inclusive) of the region to process.
        :param right: the right edge (exclusive) of the region to process.
        :param bottom: the bottom edge (exclusive) of the region to process.
        :param width: the width of the region to process.  Ignored if both
            left and right are specified.
        :param height: the height of the region to process.  Ignores if both
            top and bottom are specified.
        :param units: either 'projection', a string starting with 'proj4:',
            'epsg:', or '+proj=' or a enumerated value like 'wgs84', or one of
            the super's values.
        :param **kwargs: optional parameters.
        :returns: left, top, right, bottom, units.  The new bounds in the
            either pixel or class projection units.
        """
        if not kwargs.get('unitsWH') or kwargs.get('unitsWH') == units:
            if left is None and right is not None and width is not None:
                left = right - width
            if right is None and left is not None and width is not None:
                right = left + width
            if top is None and bottom is not None and height is not None:
                top = bottom - height
            if bottom is None and top is not None and height is not None:
                bottom = top + height
        if (left is None and right is None) or (top is None and bottom is None):
            raise TileSourceException(
                'Cannot convert from projection unless at least one of '
                'left and right and at least one of top and bottom is '
                'specified.')
        if not self.projection:
            pleft, ptop = self.toNativePixelCoordinates(
                right if left is None else left,
                bottom if top is None else top,
                units)
            pright, pbottom = self.toNativePixelCoordinates(
                left if right is None else right,
                top if bottom is None else bottom,
                units)
            units = 'base_pixels'
        else:
            inProj = self._proj4Proj(units)
            outProj = self._proj4Proj(self.projection)
            pleft, ptop = pyproj.transform(
                inProj, outProj,
                right if left is None else left,
                bottom if top is None else top)
            pright, pbottom = pyproj.transform(
                inProj, outProj,
                left if right is None else right,
                top if bottom is None else bottom)
            units = 'projection'
        left = pleft if left is not None else None
        top = ptop if top is not None else None
        right = pright if right is not None else None
        bottom = pbottom if bottom is not None else None
        return left, top, right, bottom, units

    def _getRegionBounds(self, metadata, left=None, top=None, right=None,
                         bottom=None, width=None, height=None, units=None,
                         **kwargs):
        """
        Given a set of arguments that can include left, right, top, bottom,
        width, height, and units, generate actual pixel values for left, top,
        right, and bottom.  If units is `'projection'`, use the source's
        projection.  If units starts with `'proj4:'` or `'epsg:'` or a
        custom units value, use that projection.  Otherwise, just use the super
        function.

        :param metadata: the metadata associated with this source.
        :param left: the left edge (inclusive) of the region to process.
        :param top: the top edge (inclusive) of the region to process.
        :param right: the right edge (exclusive) of the region to process.
        :param bottom: the bottom edge (exclusive) of the region to process.
        :param width: the width of the region to process.  Ignored if both
            left and right are specified.
        :param height: the height of the region to process.  Ignores if both
            top and bottom are specified.
        :param units: either 'projection', a string starting with 'proj4:',
            'epsg:' or a enumarted value like 'wgs84', or one of the super's
            values.
        :param **kwargs: optional parameters.  See above.
        :returns: left, top, right, bottom bounds in pixels.
        """
        units = TileInputUnits.get(units.lower() if units else units, units)
        # If a proj4 projection is specified, convert the left, right, top, and
        # bottom to the current projection or to pixel space if no projection
        # is used.
        if (units and (units.lower().startswith('proj4:') or
                       units.lower().startswith('epsg:') or
                       units.lower().startswith('+proj='))):
            left, top, right, bottom, units = self._convertProjectionUnits(
                left, top, right, bottom, width, height, units, **kwargs)

        if units == 'projection' and self.projection:
            bounds = self.getBounds(self.projection)
            # Fill in missing values
            if left is None:
                left = bounds['xmin'] if right is None or width is None else right - width
            if right is None:
                right = bounds['xmax'] if width is None else left + width
            if top is None:
                top = bounds['ymax'] if bottom is None or width is None else bottom - width
            if bottom is None:
                bottom = bounds['ymin'] if width is None else top + width
            if not kwargs.get('unitsWH') or kwargs.get('unitsWH') == units:
                width = height = None
            # Convert to [-0.5, 0.5], [-0.5, 0.5] coordinate range
            left = (left - self.projectionOrigin[0]) / self.unitsAcrossLevel0
            right = (right - self.projectionOrigin[0]) / self.unitsAcrossLevel0
            top = (top - self.projectionOrigin[1]) / self.unitsAcrossLevel0
            bottom = (bottom - self.projectionOrigin[1]) / self.unitsAcrossLevel0
            # Convert to world=wide 'base pixels' and crop to the world
            xScale = 2 ** (self.levels - 1) * self.tileWidth
            yScale = 2 ** (self.levels - 1) * self.tileHeight
            left = max(0, min(xScale, (0.5 + left) * xScale))
            right = max(0, min(xScale, (0.5 + right) * xScale))
            top = max(0, min(yScale, (0.5 - top) * yScale))
            bottom = max(0, min(yScale, (0.5 - bottom) * yScale))
            # Ensure correct ordering
            left, right = min(left, right), max(left, right)
            top, bottom = min(top, bottom), max(top, bottom)
            units = 'base_pixels'
        return super(MapnikFileTileSource, self)._getRegionBounds(
            metadata, left, top, right, bottom, width, height, units, **kwargs)

    @methodcache()
    def getThumbnail(self, width=None, height=None, levelZero=False, **kwargs):
        """
        Get a basic thumbnail from the current tile source.  Aspect ratio is
        preserved.  If neither width nor height is given, a default value is
        used.  If both are given, the thumbnail will be no larger than either
        size.

        :param width: maximum width in pixels.
        :param height: maximum height in pixels.
        :param levelZero: if true, always use the level zero tile.  Otherwise,
            the thumbnail is generated so that it is never upsampled.
        :param **kwargs: optional arguments.  Some options are encoding,
            jpegQuality, jpegSubsampling, and tiffCompression.
        :returns: thumbData, thumbMime: the image data and the mime type.
        """
        if self.projection:
            if ((width is not None and width < 2) or
                    (height is not None and height < 2)):
                raise ValueError('Invalid width or height.  Minimum value is 2.')
            if width is None and height is None:
                width = height = 256
            params = dict(kwargs)
            params['output'] = {'maxWidth': width, 'maxHeight': height}
            params['region'] = {'units': 'projection'}
            return self.getRegion(**params)
        return super(MapnikFileTileSource, self).getThumbnail(width, height, levelZero, **kwargs)

    def toNativePixelCoordinates(self, x, y, proj=None, roundResults=True):
        """
        Convert a coordinate in the native projection (self.getProj4String) to
        pixel coordinates.

        :param x: the x coordinate it the native projection.
        :param y: the y coordinate it the native projection.
        :param proj: input projection.  None to use the sources's projection.
        :param roundResults: if True, round the results to the nearest pixel.
        :return: (x, y) the pixel coordinate.
        """
        if proj is None:
            proj = self.projection
        # convert to the native projection
        inProj = self._proj4Proj(proj)
        outProj = self._proj4Proj(self.getProj4String())
        px, py = pyproj.transform(inProj, outProj, x, y)
        # convert to native pixel coordinates
        gt = self.dataset.GetGeoTransform()
        d = gt[2] * gt[4] - gt[1] * gt[5]
        x = (gt[0] * gt[5] - gt[2] * gt[3] - gt[5] * px + gt[2] * py) / d
        y = (gt[1] * gt[3] - gt[0] * gt[4] + gt[4] * px - gt[1] * py) / d
        if roundResults:
            x = int(round(x))
            y = int(round(y))
        return x, y

    def getPixel(self, **kwargs):
        """
        Get a single pixel from the current tile source.
        :param **kwargs: optional arguments.  Some options are region, output,
            encoding, jpegQuality, jpegSubsampling, tiffCompression, fill.  See
            tileIterator.
        :returns: a dictionary with the value of the pixel for each channel on
            a scale of [0-255], including alpha, if available.  This may
            contain additional information.
        """
        # TODO: netCDF - currently this will read the values from the
        # default subdatatset; we may want it to read values from all
        # subdatasets and the main raster bands (if they exist), and label the
        # bands better
        pixel = super(MapnikFileTileSource, self).getPixel(includeTileRecord=True, **kwargs)
        tile = pixel.pop('tile', None)
        if tile:
            # Coordinates in the max level tile
            x, y = tile['gx'], tile['gy']
            if self.projection:
                # convert to a scale of [-0.5, 0.5]
                x = 0.5 + x / 2 ** (self.levels - 1) / self.tileWidth
                y = 0.5 - y / 2 ** (self.levels - 1) / self.tileHeight
                # convert to projection coordinates
                x = self.projectionOrigin[0] + x * self.unitsAcrossLevel0
                y = self.projectionOrigin[1] + y * self.unitsAcrossLevel0
                # convert to native pixel coordinates
                x, y = self.toNativePixelCoordinates(x, y)
            if 0 <= int(x) < self.sizeX and 0 <= int(y) < self.sizeY:
                for i in range(self.dataset.RasterCount):
                    band = self.dataset.GetRasterBand(i + 1)
                    try:
                        value = band.ReadRaster(int(x), int(y), 1, 1, buf_type=gdal.GDT_Float32)
                        if value:
                            pixel.setdefault('bands', {})[i + 1] = struct.unpack('f', value)[0]
                    except RuntimeError:
                        pass
        return pixel
