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

import mapnik
import PIL.Image
import six
from osgeo import gdal
from osgeo import gdalconst
from pkg_resources import DistributionNotFound, get_distribution

from large_image import config
from large_image.cache_util import LruCacheMetaclass, methodcache
from large_image.constants import SourcePriority, TILE_FORMAT_PIL
from large_image.exceptions import TileSourceException

from large_image_source_gdal import GDALFileTileSource, InitPrefix


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


mapnik.logger.set_severity(mapnik.severity_type.Debug)


@six.add_metaclass(LruCacheMetaclass)
class MapnikFileTileSource(GDALFileTileSource):
    """
    Provides tile access to geospatial files.
    """

    cacheName = 'tilesource'
    name = 'mapnikfile'
    extensions = {
        None: SourcePriority.MEDIUM,
        'nc': SourcePriority.PREFERRED,  # netcdf
        # National Imagery Transmission Format
        'ntf': SourcePriority.HIGHER,
        'nitf': SourcePriority.HIGHER,
        'tif': SourcePriority.LOWER,
        'tiff': SourcePriority.LOWER,
        'vrt': SourcePriority.HIGHER,
    }
    mimeTypes = {
        None: SourcePriority.FALLBACK,
        'image/geotiff': SourcePriority.HIGHER,
        'image/tiff': SourcePriority.LOWER,
        'image/x-tiff': SourcePriority.LOWER,
    }

    def __init__(self, path, projection=None, unitsPerPixel=None, **kwargs):
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
                    'linear', and 'exact'.  This defaults to 'linear'.
                palette: either a list of two or more color strings, a string
                    with a dotted class name from the python palettable
                    package, or 'colortable' to use the band's color table
                    (palette).  Color strings must be parsable by mapnik's
                    Color class.  Many css strings work.  If scheme is
                    unspecified and the band is one of 'red', 'green', 'blue',
                    gray', or 'alpha', this defaults to an appropriate band
                    pair.  Otherwise, this defaults to the band's color table
                    (palette) if it has one and a black-to-white palette if it
                    does not.
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
        super(MapnikFileTileSource, self).__init__(
            path, projection=projection, unitsPerPixel=unitsPerPixel, **kwargs)

    def _checkNetCDF(self):
        """
        Check if this file is a netCDF file.  If so, get some metadata about
        available datasets.

        This assumes things about the projection that may not be true for all
        netCDF files.  It could also be extended to get better data about
        time bounds and other series data and to prevent selecting subdatasets
        that are not spatially appropriate.
        """
        if self._getDriver() != 'netCDF':
            return False
        datasets = {}
        with self._getDatasetLock:
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
                self.getBounds(InitPrefix + 'epsg:3857')
            except RuntimeError:
                self._bounds.clear()
                del self._netcdf
                return False
        with self._getDatasetLock:
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
                dataset['dataset'] = gdal.Open(dataset['name'], gdalconst.GA_ReadOnly)
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

    def _setDefaultStyle(self):
        """Don't inherit from GDAL tilesource."""
        pass

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

    def getOneBandInformation(self, band):
        if type(band) is not tuple:
            bandInfo = super(MapnikFileTileSource, self).getOneBandInformation(band)
        else:  # netcdf
            with self._getDatasetLock:
                dataset = self._netcdf['datasets'][band[0]]
                if not dataset.get('bands'):
                    if not dataset.get('dataset'):
                        dataset['dataset'] = gdal.Open(dataset['name'], gdalconst.GA_ReadOnly)
                    dataset['bands'] = self.getBandInformation(dataset['dataset'])
                bandInfo = dataset['bands'][band[1]]
        return bandInfo

    def _colorizerFromStyle(self, style):
        """
        Add a specified style to a mapnik raster symbolizer.

        :param style: a style object.
        :returns: a mapnik raster colorizer.
        """
        try:
            scheme = style.get('scheme', 'linear')
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
            colors = style.get('palette', ['#000000', '#ffffff'])
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

    def addStyle(self, m, layerSrs, extent=None):
        """
        Attaches raster style option to mapnik raster layer and adds the layer
        to the mapnik map.

        :param m: mapnik map.
        :param layerSrs: the layer projection
        :param extent: the extent to use for the mapnik layer.
        """
        style = self._styleBands()
        bands = self.getBandInformation()
        if not len(style):
            style.append({'band': -1})
        config.getConfig('logger').debug(
            'mapnik addTile specified style: %r, used style %r',
            getattr(self, 'style', None), style)
        for styleBand in style:
            if styleBand['band'] != -1:
                colorizer = self._colorizerFromStyle(styleBand)
                composite = getattr(mapnik.CompositeOp, styleBand.get(
                    'composite', 'multiply' if styleBand['band'] == 'alpha' else 'lighten'))
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
                if self._proj4Proj(layerSrs).crs.is_geographic:
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
        if self.projection:
            # If we are using a projection, the tile could contain no data.
            # Don't bother having mapnik render the blank tile -- just output
            # it.
            bounds = self.getBounds(self.projection)
            if (xmin >= bounds['xmax'] or xmax <= bounds['xmin'] or
                    ymin >= bounds['ymax'] or ymax <= bounds['ymin']):
                pilimg = PIL.Image.new('RGBA', (self.tileWidth, self.tileHeight))
                return self._outputTile(
                    pilimg, TILE_FORMAT_PIL, x, y, z, applyStyle=False, **kwargs)
        if overscan:
            pw = (xmax - xmin) / self.tileWidth
            py = (ymax - ymin) / self.tileHeight
            xmin, xmax = xmin - pw * overscan, xmax + pw * overscan
            ymin, ymax = ymin - py * overscan, ymax + py * overscan
        with self._getTileLock:
            if not hasattr(self, '_mapnikMap'):
                mapnik.logger.set_severity(mapnik.severity_type.Debug)
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
        return self._outputTile(pilimg, TILE_FORMAT_PIL, x, y, z, applyStyle=False, **kwargs)
