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

import math
import pathlib
import struct
import tempfile
import threading
from urllib.parse import urlencode, urlparse

import numpy as np
import PIL.Image
import rasterio as rio
from rasterio.errors import RasterioIOError
import pyproj

import large_image
from large_image.cache_util import CacheProperties, LruCacheMetaclass, methodcache
from large_image.constants import (
    TILE_FORMAT_IMAGE,
    TILE_FORMAT_NUMPY,
    TILE_FORMAT_PIL,
    SourcePriority,
    TileInputUnits,
    TileOutputMimeTypes,
)
from large_image.exceptions import (
    TileSourceError,
    TileSourceFileNotFoundError,
    TileSourceInefficientError,
)
from large_image.tilesource import FileTileSource
from large_image.tilesource.utilities import getPaletteColors

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

TileInputUnits["projection"] = "projection"
TileInputUnits["proj"] = "projection"
TileInputUnits["wgs84"] = "proj4:EPSG:4326"
TileInputUnits["4326"] = "proj4:EPSG:4326"

# Inform the tile source cache about the potential size of this tile source
CacheProperties["tilesource"]["itemExpectedSize"] = max(
    CacheProperties["tilesource"]["itemExpectedSize"], 100 * 1024**2
)

# Used to cache pixel size for projections
ProjUnitsAcrossLevel0 = {}
ProjUnitsAcrossLevel0_MaxSize = 100


class RasterioFileTileSource(FileTileSource, metaclass=LruCacheMetaclass):
    """
    Provides tile access to geospatial files.
    """

    cacheName = "tilesource"
    name = "rasterio"
    extensions = {
        None: SourcePriority.MEDIUM,
        "geotiff": SourcePriority.PREFERRED,
        "ntf": SourcePriority.PREFERRED,
        "nitf": SourcePriority.PREFERRED,
        "tif": SourcePriority.LOW,
        "tiff": SourcePriority.LOW,
        "vrt": SourcePriority.PREFERRED,
    }
    mimeTypes = {
        None: SourcePriority.FALLBACK,
        "image/geotiff": SourcePriority.PREFERRED,
        "image/tiff": SourcePriority.LOW,
        "image/x-tiff": SourcePriority.LOW,
    }
    geospatial = True

    def __init__(self, path, projection=None, unitsPerPixel=None, **kwargs):
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: a filesystem path for the tile source.
        :param projection: None to use pixel space, otherwise a crs compatible with pyproj.
        :param unitsPerPixel: The size of a pixel at the 0 tile size.
            Ignored if the projection is None.  For projections, None uses the default,
            which is the distance between (-180,0) and (180,0) in EPSG:4326 converted to the
            projection divided by the tile size. crs projections that are not latlong
            (is_geographic is False) must specify unitsPerPixel.
        """

        # init the object
        super().__init__(path, **kwargs)

        # set the large_image path
        self._largeImagePath = self._getLargeImagePath()

        # open the file with rasterio
        try:
            self.dataset = rio.open(self._largeImagePath)
        except RasterioIOError:
            raise TileSourceError("File cannot be opened via rasterio.")
        except FileNotFoundError:
            raise TileSourceFileNotFoundError(self._largeImagePath)

        # create a thred lock
        self._getDatasetLock = threading.RLock()

        # extract default parameters from the image
        self.tileSize = 256
        self._bounds = {}
        self.tileWidth = self.tileSize
        self.tileHeight = self.tileSize
        self._projection = pyproj.crs.CRS(projection) if projection else None

        # get width and height parameters
        with self._getDatasetLock:
            self.sourceSizeX = self.sizeX = self.dataset.width
            self.sourceSizeY = self.sizeY = self.dataset.height

        # netCFD is blacklisted from rasterio so it won't be used.
        # use the gdal binding if needed. This variable is always ignored
        # is_netcdf = False

        # get the different scales and projections from the image
        scale = self.getPixelSizeInMeters()

        # raise an error if we are missing some information about the projection
        # i.e. we don't know where to place it on a map
        isProjected = self.projection or self.dataset.driver.lower() == "png"
        if isProjected and not scale:
            raise TileSourceError(
                "File does not have a projected scale, "
                "so will not be opened via rasterio with a projection."
            )

        # set the levels of the tiles
        logX = math.log(float(self.sizeX) / self.tileWidth)
        logY = math.log(float(self.sizeY) / self.tileHeight)
        computedLevel = math.ceil(max(logX, logY) / math.log(2))
        self.sourceLevels = self.levels = int(max(0, computedLevel) + 1)

        self._unitsPerPixel = unitsPerPixel
        self.projection is None or self._initWithProjection(unitsPerPixel)
        self._getTileLock = threading.Lock()
        self._setDefaultStyle()

    def _getLargeImagePath(self):
        """
        Get rasterio-compatible image path.

        This will cast the output to a string and can also handle
        URLs ('http', 'https', 'ftp', 's3') for use with fiona
        `Virtual Filesystems Interface <https://gdal.org/user/virtual_file_systems.html>`_.
        """

        # init with largeimage full path
        path = str(self.largeImagePath)

        # check if it's remote and update the str accordingly
        supportedScheme = {"http", "https", "ftp", "s3"}
        if urlparse(path).scheme in supportedScheme:
            if path.startswith("s3://"):
                s3Path = path.replace("s3://", "")
                path = f"/vsis3/{s3Path}"
            else:
                rasterioOptions = {
                    "url": path,
                    "use_head": "no",
                    "list_dir": "no",
                }
                path = f"/vsicurl?{urlencode(rasterioOptions)}"

        return path

    def _styleBands(self):

        interpColorTable = {
            "red": ["#000000", "#ff0000"],
            "green": ["#000000", "#00ff00"],
            "blue": ["#000000", "#0000ff"],
            "gray": ["#000000", "#ffffff"],
            "alpha": ["#ffffff00", "#ffffffff"],
        }
        style = []
        if hasattr(self, "style"):
            styleBands = self.style["bands"] if "bands" in self.style else [self.style]
            for styleBand in styleBands:

                styleBand = styleBand.copy()
                # Default to band 1 -- perhaps we should default to gray or
                # green instead.
                styleBand["band"] = self._bandNumber(styleBand.get("band", 1))
                style.append(styleBand)

        if not len(style):
            for interp in ("red", "green", "blue", "gray", "palette", "alpha"):
                band = self._bandNumber(interp, False)
                # If we don't have the requested band, or we only have alpha,
                # or this is gray or palette and we already added another band,
                # skip this interpretation.
                if (
                    band is None
                    or (interp == "alpha" and not len(style))
                    or (interp in ("gray", "palette") and len(style))
                ):
                    continue

                if interp == "palette":
                    bandInfo = self.getOneBandInformation(band)
                    style.append(
                        {
                            "band": band,
                            "palette": "colortable",
                            "min": 0,
                            "max": len(bandInfo["colortable"]) - 1,
                        }
                    )
                else:
                    style.append(
                        {
                            "band": band,
                            "palette": interpColorTable[interp],
                            "min": "auto",
                            "max": "auto",
                            "nodata": "auto",
                            "composite": "multiply" if interp == "alpha" else "lighten",
                        }
                    )

        return style

    def _setDefaultStyle(self):
        """
        If not style was specified, create a default style.
        """

        if hasattr(self, "style"):
            styleBands = self.style["bands"] if "bands" in self.style else [self.style]
            if not len(styleBands) or (
                len(styleBands) == 1
                and isinstance(styleBands[0].get("band", 1), int)
                and styleBands[0].get("band", 1) <= 0
            ):
                del self.style
        style = self._styleBands()
        if len(style):
            hasAlpha = False
            for bstyle in style:
                interp = self.getOneBandInformation(bstyle.get("band", 0)).get(
                    "interpretation"
                )
                hasAlpha = hasAlpha or interp == "alpha"
                if "palette" in bstyle:
                    if bstyle["palette"] == "colortable":
                        bandInfo = self.getOneBandInformation(bstyle.get("band", 0))
                        color = lambda i: "#" + i * "{:x02}"  # noqa E731
                        bstyle["palette"] = [
                            (color(len(entry)).format(entry))
                            for entry in bandInfo["colortable"]
                        ]
                    else:
                        bstyle["palette"] = self.getHexColors(bstyle["palette"])
                if bstyle.get("nodata") == "auto":
                    bandInfo = self.getOneBandInformation(bstyle.get("band", 0))
                    bstyle["nodata"] = bandInfo.get("nodata", None)
            if not hasAlpha and self.projection:
                style.append(
                    {
                        "band": len(self.getBandInformation()) + 1,
                        "min": 0,
                        "max": "auto",
                        "composite": "multiply",
                        "palette": ["#ffffff00", "#ffffffff"],
                    }
                )
            self.logger.debug("Using style %r", style)
            self.style = {"bands": style}
        self._bandNames = {}
        for idx, band in self.getBandInformation().items():
            if band.get("interpretation"):
                self._bandNames[band["interpretation"].lower()] = idx

    def _scanForMinMax(self, dtype, frame=0, analysisSize=1024, onlyMinMax=True):
        """
        Update the band range of the data type to the end of the range list.

        This will change autocalling behavior, and for non-integer data types,
        this adds the range [0, 1].

        :param dtype: the dtype of the bands
        :param frame: optional default to 0
        :param analysisSize: optional default to 1024
        :param onlyMinMax: optional default to True
        """

        bandInfo = self.getBandInformation()

        # get the minmax value from the band
        hasMin = all(b.get("min") is not None for b in bandInfo.values())
        hasMax = all(b.get("max") is not None for b in bandInfo.values())
        if not frame and onlyMinMax and hasMax and hasMin:
            with self._getDatasetLock:
                dtype = self.dataset.dtype
            self._bandRanges[0] = {
                "min": np.array([b["min"] for b in bandInfo.values()], dtype=dtype),
                "max": np.array([b["max"] for b in bandInfo.values()], dtype=dtype),
            }
        else:
            kwargs = {}
            if self.projection:
                bounds = self.getBounds(self.projection)
                kwargs = {
                    "region": {
                        "left": bounds["xmin"],
                        "top": bounds["ymax"],
                        "right": bounds["xmax"],
                        "bottom": bounds["ymin"],
                        "units": "projection",
                    }
                }
            super(RasterioFileTileSource, RasterioFileTileSource)._scanForMinMax(
                self,
                dtype=dtype,
                frame=frame,
                analysisSize=analysisSize,
                onlyMinMax=onlyMinMax,
                **kwargs,
            )

        # Add the maximum range of the data type to the end of the band
        # range list.  This changes autoscaling behavior.  For non-integer
        # data types, this adds the range [0, 1].
        rangeMax = np.iinfo(dtype).max if isinstance(dtype, np.integer) else 1
        self._bandRanges[frame]["max"] = np.append(
            self._bandRanges[frame]["max"], rangeMax
        )
        self._bandRanges[frame]["min"] = np.append(self._bandRanges[frame]["min"], 0)

    def _initWithProjection(self, unitsPerPixel=None):
        """
        Initialize aspects of the class when a projection is set.

        :param unitsPerPixel: optional default to None
        """

        inProj = pyproj.crs.CRS(4326)
        # Since we already converted to bytes decoding is safe here
        outProj = self.projection
        if outProj.is_geographic:
            raise TileSourceError(
                "Projection must not be geographic (it needs to use linear "
                "units, not longitude/latitude)."
            )

        if unitsPerPixel is not None:
            self.unitsAcrossLevel0 = float(unitsPerPixel) * self.tileSize
        else:
            self.unitsAcrossLevel0 = ProjUnitsAcrossLevel0.get(self.projection.srs)
            if self.unitsAcrossLevel0 is None:
                # If unitsPerPixel is not specified, the horizontal distance
                # between -180,0 and +180,0 is used.  Some projections (such as
                # stereographic) will fail in this case; they must have a unitsPerPixel specified.
                equator = pyproj.transformer.Transformer.from_proj(
                    inProj, outProj, always_xy=True
                )
                xx, yy = equator.transform([-180, 180], [0, 0])
                self.unitsAcrossLevel0 = abs(xx[1] - xx[0])
                if not self.unitsAcrossLevel0:
                    raise TileSourceError(
                        "unitsPerPixel must be specified for this projection"
                    )
                if len(ProjUnitsAcrossLevel0) >= ProjUnitsAcrossLevel0_MaxSize:
                    ProjUnitsAcrossLevel0.clear()
                ProjUnitsAcrossLevel0[self.projection.srs] = self.unitsAcrossLevel0

        # This was
        #   self.projectionOrigin = pyproj.transformer(inProj, outProj, 0, 0)
        # but for consistency, it should probably always be (0, 0).  Whatever
        # renders the map would need the same offset as used here.
        self.projectionOrigin = (0, 0)

        # Calculate values for this projection
        width = self.getPixelSizeInMeters() * self.tileWidth
        tile0 = self.unitsAcrossLevel0 / width
        base2 = math.ceil(math.log(tile0) / math.log(2))
        self.levels = int(max(int(base2) + 1, 1))

        # Report sizeX and sizeY as the whole world
        self.sizeX = 2 ** (self.levels - 1) * self.tileWidth
        self.sizeY = 2 ** (self.levels - 1) * self.tileHeight

    @staticmethod
    def getLRUHash(*args, **kwargs):
        """
        TODO docstring
        """

        projection = kwargs.get("projection", args[1] if len(args) >= 2 else None)
        unitsPerPixel = kwargs.get("unitsPerPixel", args[3] if len(args) >= 4 else None)

        info = f",{projection},{unitsPerPixel}"

        return (
            super(RasterioFileTileSource, RasterioFileTileSource).getLRUHash(
                *args, **kwargs
            )
            + info
        )

    def getState(self):
        return super().getState() + f",{self._projection.srs},{self._unitsPerPixel}"

    @staticmethod
    def getHexColors(palette):
        """
        Returns list of hex colors for a given color palette

        :param palette: the color palette

        :returns: List of colors
        """

        # get the palette as int values
        palette = getPaletteColors(palette)
        palette = [[int(v) for v in c] for c in palette]

        return ["#{:02x}{:02x}{:02x}{:02x}".format(*c) for c in palette]

    def getCrs(self):
        """
        Returns crs for the given dataset

        :returns: The crs or None.
        """

        with self._getDatasetLock:

            # use gcp if available
            if len(self.dataset.gcps[0]) != 0 and self.dataset.gcps[1]:
                crs = self.dataset.gcps[1]
            else:
                crs = self.dataset.crs

            # if no crs is set consider it unprojected in epsg:4326
            crs = crs or pyproj.crs.CRS(4326)

            return crs

    def getPixelSizeInMeters(self):
        """
        Get the approximate base pixel size in meters.  This is calculated as
        the average scale of the four edges in the WGS84 ellipsoid.

        :returns: the pixel size in meters or None.
        """

        bounds = self.getBounds("epsg:4326")
        geod = pyproj.Geod(ellps="WGS84")

        # extract the corner corrdinates
        ll = bounds["xmin"], bounds["ymin"]
        ul = bounds["xmin"], bounds["ymax"]
        lr = bounds["xmax"], bounds["ymin"]
        ur = bounds["xmax"], bounds["ymax"]

        # compute the geods from the different corners of the image
        az12, az21, s1 = geod.inv(*ul, *ur)
        az12, az21, s2 = geod.inv(*ur, *lr)
        az12, az21, s3 = geod.inv(*lr, *ll)
        az12, az21, s4 = geod.inv(*ll, *ul)

        return (s1 + s2 + s3 + s4) / (self.sourceSizeX * 2 + self.sourceSizeY * 2)

    def getNativeMagnification(self):
        """
        Get the magnification at the base level.

        :return: width of a pixel in mm, height of a pixel in mm.
        """

        scale = self.getPixelSizeInMeters()
        return {
            "magnification": None,
            "mm_x": scale * 100 if scale else None,
            "mm_y": scale * 100 if scale else None,
        }

    def _getGeoTransform(self):
        """
        Get the GeoTransform.  If GCPs are used, get the appropriate transform
        for those.

        :returns: a six-component array with the transform
        """

        with self._getDatasetLock:
            gt = self.dataset.transform
            if len(self.dataset.gcps[0]) != 0 and self.dataset.gcps[1]:
                gt = rio.transform.from_gcps(self.dataset.gcps[0])

        return gt

    def getBounds(self, crs=None):
        """
        Returns bounds of the image.

        :param crs: the projection for the bounds.  None for the default.

        :returns: an object with the four corners and the projection that was used.
            None if we don't know the original projection.
        """

        # read the crs as a crs if needed
        dstCrs = pyproj.crs.CRS(crs) if crs is not None else None

        # exit if it's already set
        if dstCrs.srs in self._bounds:
            return self._bounds[dstCrs.srs]

        # extract the projection informations
        with self._getDatasetLock:
            srcCrs = self.dataset.crs  # it should always be there
            xmin, ymin, xmax, ymax = self.dataset.bounds

        # convert his coordinates in the destination projection system
        if srcCrs.is_geographic and dstCrs is not None and dstCrs != srcCrs:

            # create a transformer between the 2 values
            t = pyproj.transformer.Transformer.from_crs(srcCrs, dstCrs)
            (xmin, xmax), (ymin, ymax) = t.transform([xmin, xmax], [ymin, ymax])

        # build the bounds dict
        bounds = {
            "srs": dstCrs.srs,
            "xmin": xmin,
            "ymin": ymin,
            "xmax": xmax,
            "ymax": ymax,
        }

        self._bounds[dstCrs.srs] = bounds

        return bounds

    def getBandInformation(self, statistics=True, dataset=None, **kwargs):
        """
        Get information about each band in the image.

        :param statistics: if True, compute statistics if they don't already exist.
            Ignored: always treated as True.
        :param dataset: the dataset.  If None, use the main dataset.

        :returns: a list of one dictionary per band.  Each dictionary contains
            known values such as interpretation, min, max, mean, stdev, nodata,
            scale, offset, units, categories, colortable, maskband.
        """

        # exit if the value is already set
        if getattr(self, "_bandInfo", None) and not dataset:
            return self._bandInfo

        # do everything inside the dataset lock to avoid multiple read
        with self._getDatasetLock:

            # setup the dataset (use the one store in self.dataset if not cached)
            cache = not dataset
            if not dataset:
                dataset = self.dataset

            # loop in the bands to get the indicidak stats (bands are 1 indexed)
            infoSet = {}
            for i in range(dataset.count):

                # get the stats
                stats = dataset.statistics(i + 1)

                info = {
                    "min": stats.min,
                    "max": stats.max,
                    "mean": stats.mean,
                    "stdev": stats.std,
                    "nodata": dataset.nodatavals[i],
                    "scale": dataset.scales[i],
                    "offset": dataset.offsets[i],
                    "units": dataset.units[i],
                    "categories": dataset.descriptions[i],
                    "interpretation": dataset.colorinterp[i],
                    "maskband": dataset.read_mask(i + 1),
                }

                # add extra informations if available
                try:
                    info.update(colortable=dataset.colormap(i + 1))
                except ValueError:
                    pass

                # Only keep values that aren't None or the empty string
                infoSet[i + 1] = {k: v for k, v in info.items() if v not in (None, "")}

        # set the value to cache if needed
        cache is False or setattr(self, "_bandInfo", infoSet)

        return infoSet

    def getMetadata(self):

        with self._getDatasetLock:

            metadata = {
                "geospatial": True,
                "levels": self.levels,
                "sizeX": self.sizeX,
                "sizeY": self.sizeY,
                "sourceLevels": self.sourceLevels,
                "sourceSizeX": self.sourceSizeX,
                "sourceSizeY": self.sourceSizeY,
                "tileWidth": self.tileWidth,
                "tileHeight": self.tileHeight,
                "bounds": self.getBounds(self.projection),
                "sourceBounds": self.getBounds(),
                "bands": self.getBandInformation(),
            }

        # magnification is computed elswhere
        metadata.update(self.getNativeMagnification())

        return metadata

    def getInternalMetadata(self, **kwargs):
        """
        Return additional known metadata about the tile source.
        Data returned from this method is not guaranteed to be in
        any particular format or have specific values.

        :returns: a dictionary of data or None.
        """

        result = {}
        with self._getDatasetLock:
            result["driverShortName"] = self.dataset.driver
            result["driverLongName"] = self.dataset.driver
            # result['fileList'] = self.dataset.GetFileList()
            result["RasterXSize"] = self.dataset.width
            result["RasterYSize"] = self.dataset.height
            result["GeoTransform"] = self._getGeoTransform()
            result["Projection"] = self.dataset.crs
            result["strProjection"] = self.dataset.crs.to_string()
            result["GCPProjection"] = self.dataset.gcps[1]
            result["Metadata"] = self.dataset.meta

            # add gcp of available
            if len(self.dataset.gcp[0]) != 0:
                result["GCPs"] = [
                    {
                        "id": gcp.id,
                        "line": gcp.row,
                        "pixel": gcp.col,
                        "x": gcp.x,
                        "y": gcp.y,
                        "z": gcp.z,
                        "info": gcp.info,
                    }
                    for gcp in self.dataset.gcp[0]
                ]

            # TODO need to check but I think it's useless

            # result['Metadata'] = self.dataset.GetMetadata_List()
            # for key in ['IMAGE_STRUCTURE', 'SUBDATASETS', 'GEOLOCATION', 'RPC']:
            #    metadatalist = self.dataset.GetMetadata_List(key)
            #    if metadatalist:
            #        result['Metadata_' + key] = metadatalist

        return result

    def getTileCorners(self, z, x, y):
        """
        Returns bounds of a tile for a given x,y,z index.

        :param z: tile level
        :param x: tile offset from left
        :param y: tile offset from right

        :returns: (xmin, ymin, xmax, ymax) in the current projection or base pixels.
        """

        x, y = float(x), float(y)

        if self.projection:

            # Scale tile into the range [-0.5, 0.5], [-0.5, 0.5]
            xmin = -0.5 + x / 2.0**z
            xmax = -0.5 + (x + 1) / 2.0**z
            ymin = 0.5 - (y + 1) / 2.0**z
            ymax = 0.5 - y / 2.0**z

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

    def _bandNumber(self, band, exc=True):
        """
        Given a band number or interpretation name, return a validated band number.

        :param band: either -1, a positive integer, or the name of a band interpretation
            that is present in the tile source.
        :param exc: if True, raise an exception if no band matches.

        :returns: a validated band, either 1 or a positive integer, or None if no
            matching band and exceptions are not enabled.
        """

        # retreive the bands informations from the initial dataset or cache
        bands = self.getBandInformation()

        # search for the band with multiple methods
        if hasattr(band, "isdigit") and band.isdigit():
            band = int(band)
        elif isinstance(band, str):
            band = next((i for i in bands if band == bands[i]["interpretation"]), None)

        # set to None if not included in the possible band values
        isBandNumber = band != -1 and band not in bands
        band = band if isBandNumber else None

        # raise an error if the band is not inside the dataset only if
        # requested from the function call
        if exc is True and band is None:
            raise TileSourceError(
                "Band has to be a positive integer, -1, or a band "
                "interpretation found in the source."
            )

        return band

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False, **kwargs):
        """
        TODO missing docstring
        """

        if not self.projection:

            self._xyzInRange(x, y, z)
            factor = int(2 ** (self.levels - 1 - z))
            xmin = int(x * factor * self.tileWidth)
            ymin = int(y * factor * self.tileHeight)
            xmax = int(min(xmin + factor * self.tileWidth, self.sourceSizeX))
            ymax = int(min(ymin + factor * self.tileHeight, self.sourceSizeY))
            w = int(max(1, round((xmax - xmin) / factor)))
            h = int(max(1, round((ymax - ymin) / factor)))

            with self._getDatasetLock:
                window = rio.windows.Window(xmin, ymin, xmax - xmin, ymax - ymin)
                count = self.dataset.count
                tile = self.dataset.read(window=window, out_shape=(count, w, h))

        else:
            xmin, ymin, xmax, ymax = self.getTileCorners(z, x, y)
            bounds = self.getBounds(self.projection)

            # return empty image when I'm out of bounds
            if (
                xmin >= bounds["xmax"]
                or xmax <= bounds["xmin"]
                or ymin >= bounds["ymax"]
                or ymax <= bounds["ymin"]
            ):
                pilimg = PIL.Image.new("RGBA", (self.tileWidth, self.tileHeight))
                return self._outputTile(
                    pilimg, TILE_FORMAT_PIL, x, y, z, applyStyle=False, **kwargs
                )

            # read the image as a warp vrt
            with self._getDatasetLock:
                with rio.vrt.WarpedVRT(self.dataset, crs=self.projection) as vrt:
                    window = vrt.window(xmin, ymin, xmax, ymax)

                    # TODO understand how to define the width and height of the tile itself
                    # what is written here seems false
                    outShape = (self.tileWidth, self.tileHeight, self.dataset.count)
                    tile = vrt.read(window=window, out_shape=outShape)

            # if necessary for multispectral images set the coordinates first and the
            # bands at the end
            if len(tile.shape) == 3:
                tile = np.moveaxis(tile, 0, 3)

        return self._outputTile(
            tile, TILE_FORMAT_NUMPY, x, y, z, pilImageAllowed, numpyAllowed, **kwargs
        )

    def _convertProjectionUnits(
        self, left, top, right, bottom, width, height, units, **kwargs
    ):
        """
        Given bound information and a units that consists of a projection (srs or crs),
        convert the bounds to either pixel or the class projection coordinates.

        :param left: the left edge (inclusive) of the region to process.
        :param top: the top edge (inclusive) of the region to process.
        :param right: the right edge (exclusive) of the region to process.
        :param bottom: the bottom edge (exclusive) of the region to process.
        :param width: the width of the region to process.  Ignored if both left and
            right are specified.
        :param height: the height of the region to process.  Ignores if both top and
            bottom are specified.
        :param units: either 'projection', a string starting with 'proj4:','epsg:',
            or '+proj=' or a enumerated value like 'wgs84', or one of the super's values.
        :param kwargs: optional parameters.

        :returns: left, top, right, bottom, units.  The new bounds in the either
            pixel or class projection units.
        """

        # build the different corner from the parameters
        if not kwargs.get("unitsWH") or kwargs.get("unitsWH") == units:
            if left is None and right is not None and width is not None:
                left = right - width
            if right is None and left is not None and width is not None:
                right = left + width
            if top is None and bottom is not None and height is not None:
                top = bottom - height
            if bottom is None and top is not None and height is not None:
                bottom = top + height

        # raise error if we didn't build one of the coordinates
        if (left is None and right is None) or (top is None and bottom is None):
            raise TileSourceError(
                "Cannot convert from projection unless at least one of "
                "left and right and at least one of top and bottom is "
                "specified."
            )

        # compute the pixel coordinates of the corners if no projection is set
        if not self.projection:
            pleft, ptop = self.toNativePixelCoordinates(
                right if left is None else left, bottom if top is None else top, units
            )
            pright, pbottom = self.toNativePixelCoordinates(
                left if right is None else right,
                top if bottom is None else bottom,
                units,
            )
            units = "base_pixels"

        # compute the coordinates if the projection exist
        else:
            with self._getDatasetLock:
                srcCrs = self.dataset.crs
            dstCrs = self.projection

            transformer = pyproj.transformer.Transformer.from_crs(
                srcCrs, dstCrs, always_xy=True
            )
            pleft, ptop = transformer.transform(left or right, top or bottom)
            pright, pbottom = transformer.transform(right or left, bottom or top)
            units = "projection"

        # set the corner value in pixel coordinates if the coordinate was initially
        # set else leave it to None
        left = pleft if left is not None else None
        top = ptop if top is not None else None
        right = pright if right is not None else None
        bottom = pbottom if bottom is not None else None

        return left, top, right, bottom, units

    def _getRegionBounds(
        self,
        metadata,
        left=None,
        top=None,
        right=None,
        bottom=None,
        width=None,
        height=None,
        units=None,
        **kwargs,
    ):
        """
        Given a set of arguments that can include left, right, top, bottom, width,
        height, and units, generate actual pixel values for left, top, right, and bottom.
        If units is `'projection'`, use the source's projection.  If units is a
        proj string, use that projection.  Otherwise, just use the super function.

        :param metadata: the metadata associated with this source.
        :param left: the left edge (inclusive) of the region to process.
        :param top: the top edge (inclusive) of the region to process.
        :param right: the right edge (exclusive) of the region to process.
        :param bottom: the bottom edge (exclusive) of the region to process.
        :param width: the width of the region to process.  Ignored if both left and
            right are specified.
        :param height: the height of the region to process.  Ignores if both top and
            bottom are specified.
        :param units: either 'projection', a string starting with 'proj4:', 'epsg:'
            or a enumarted value like 'wgs84', or one of the super's values.
        :param kwargs: optional parameters from _convertProjectionUnits.  See above.

        :returns: left, top, right, bottom bounds in pixels.
        """

        isUnits = units is not None
        units = TileInputUnits.get(units.lower() if isUnits else None, units)

        # convert the coordinates if a projection exist
        if isUnits:
            left, top, right, bottom, units = self._convertProjectionUnits(
                left, top, right, bottom, width, height, units, **kwargs
            )

        if units == "projection" and self.projection:
            bounds = self.getBounds(self.projection)

            # Fill in missing values
            if left is None:
                left = (
                    bounds["xmin"] if right is None or width is None else right - width
                )
            if right is None:
                right = bounds["xmax"] if width is None else left + width
            if top is None:
                top = (
                    bounds["ymax"]
                    if bottom is None or height is None
                    else bottom - width
                )
            if bottom is None:
                bottom = bounds["ymin"] if height is None else top + width

            # remove width and height if necessary
            if not kwargs.get("unitsWH") or kwargs.get("unitsWH") == units:
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
            units = "base_pixels"

        return super()._getRegionBounds(
            metadata, left, top, right, bottom, width, height, units, **kwargs
        )

    def pixelToProjection(self, x, y, level=None):
        """
        Convert from pixels back to projection coordinates.

        :param x, y: base pixel coordinates.
        :param level: the level of the pixel.  None for maximum level.

        :returns: px, py in projection coordinates.
        """

        if level is None:
            level = self.levels - 1

        # if no projection is set build the pixel values using the geotransform
        if not self.projection:
            gt = self._getGeoTransform()
            x *= 2 ** (self.levels - 1 - level)
            y *= 2 ** (self.levels - 1 - level)
            x = gt[0] + gt[1] * x + gt[2] * y
            y = gt[3] + gt[4] * x + gt[5] * y

        # else we used the projection set in __init__
        else:
            xScale = 2**level * self.tileWidth
            yScale = 2**level * self.tileHeight
            x = x / xScale - 0.5
            y = 0.5 - y / yScale
            x = x * self.unitsAcrossLevel0 + self.projectionOrigin[0]
            y = y * self.unitsAcrossLevel0 + self.projectionOrigin[1]

        return x, y

    @methodcache()
    def getThumbnail(self, width=None, height=None, **kwargs):
        """
        Get a basic thumbnail from the current tile source.  Aspect ratio is preserved.
        If neither width nor height is given, a default value is used.  If both are given,
        the thumbnail will be no larger than either size.  A thumbnail has the same
        options as a region except that it always includes the entire image if there
        is no projection and has a default size of 256 x 256.

        :param width: maximum width in pixels.
        :param height: maximum height in pixels.
        :param kwargs: optional arguments.  Some options are encoding, jpegQuality,
            jpegSubsampling, and tiffCompression.

        :returns: thumbData, thumbMime: the image data and the mime type.
        """

        if self.projection:

            # image is too small if the size is None or 1 pixels or lower
            noWidth = width is not None and width < 2
            noHeight = height is not None and height < 2
            if noWidth or noHeight:
                raise ValueError("Invalid width or height.  Minimum value is 2.")

            # fix image size to 256x256 if needed
            if width is None and height is None:
                width = height = 256

            params = dict(kwargs)
            params["output"] = {"maxWidth": width, "maxHeight": height}
            params["region"] = {"units": "projection"}

            return self.getRegion(**params)

        # if no prjection is found, call the thumbnail method for non geogrpahic images
        return super().getThumbnail(width, height, **kwargs)

    def toNativePixelCoordinates(self, x, y, crs=None, roundResults=True):
        """
        Convert a coordinate in the native projection to pixel coordinates.

        :param x: the x coordinate it the native projection.
        :param y: the y coordinate it the native projection.
        :param crs: input projection.  None to use the sources's projection.
        :param roundResults: if True, round the results to the nearest pixel.

        :return: (x, y) the pixel coordinate.
        """

        srcCrs = self.projection if crs is None else pyproj.crs.CRS(crs)

        # convert to the native projection
        dstCrs = pyproj.crs.CRS(self.getCrs())
        transformer = pyproj.transformer.Transformer.from_crs(
            srcCrs, dstCrs, always_xy=True
        )
        px, py = transformer.transform(x, y)

        # convert to native pixel coordinates
        gt = self._getGeoTransform()
        d = gt[2] * gt[4] - gt[1] * gt[5]
        x = (gt[0] * gt[5] - gt[2] * gt[3] - gt[5] * px + gt[2] * py) / d
        y = (gt[1] * gt[3] - gt[0] * gt[4] + gt[4] * px - gt[1] * py) / d

        # convert to integer if requested
        if roundResults:
            x, y = int(round(x)), int(round(y))

        return x, y

    def getPixel(self, **kwargs):
        """
        Get a single pixel from the current tile source.

        :param kwargs: optional arguments.  Some options are region, output, encoding,
            jpegQuality, jpegSubsampling, tiffCompression, fill.  See tileIterator.

        :returns: a dictionary with the value of the pixel for each channel on a
            scale of [0-255], including alpha, if available.  This may contain
            additional information.
        """

        # TODO: netCFD - currently this will read the values from the
        # default subdatatset; we may want it to read values from all
        # subdatasets and the main raster bands (if they exist), and label the
        # bands better
        pixel = super().getPixel(includeTileRecord=True, **kwargs)
        tile = pixel.pop("tile", None)

        if tile:

            # Coordinates in the max level tile
            x, y = tile["gx"], tile["gy"]

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
                with self._getDatasetLock:
                    for i in range(self.dataset.count):
                        window = rio.window.Window(int(x), int(y), 1, 1)
                        try:
                            value = self.dataset.read(i + 1, window=window).astype(
                                np.single
                            )
                            value = value[0][0]  # there should be 1 single pixel
                            pixel.setdefault("bands", {})[i + 1] = struct.unpack(
                                "f", value
                            )[0]
                        except RuntimeError:
                            pass

        return pixel

    def _encodeTiledImageFromVips(self, vimg, iterInfo, image, **kwargs):
        """
        Save a vips image as a tiled tiff.

        :param vimg: a vips image.
        :param iterInfo: information about the region based on the tile iterator.
        :param image: a record with partial vips images and the current output size.

        Additional parameters are available as kwargs.

        :param compression: the internal compression format.  This can handle a
            variety of options similar to the converter utility.

        :returns: a pathlib.Path of the output file and the output mime type.
        """

        # set up the parameters for conversion on vips image
        convertParams = large_image.tilesource.base._vipsParameters(
            defaultCompression="lzw", **kwargs
        )
        convertParams.pop("pyramid", None)

        isCompressed = convertParams["compression"] in {"webp", "jpeg"}
        vimg = large_image.tilesource.base._vipsCast(vimg, isCompressed)

        # write the data to a temp file to make it readable for rasterio
        with tempfile.NamedTemporaryFile(suffix=".tiff", prefix="tiledRegion_") as f:
            vimg.write_to_file(f, **convertParams)

            # write the data to an outputFile this file will be deleted manually
            with rio.open(f.name) as src, tempfile.NamedTemporaryFile(
                suffix=".tiff", prefix="tiledGeoRegion_", delete=False
            ) as output:

                # extract information from the iterInfo
                top = iterInfo["region"]["top"]
                left = iterInfo["region"]["left"]
                bottom = iterInfo["region"]["bottom"]
                right = iterInfo["region"]["right"]
                dstCrs = pyproj.crs.CRS(iterInfo["metadata"]["bounds"]["srs"])

                # compute the transformation
                transform, width, height = rio.warp.calculate_default_transform(
                    src.crs,
                    dstCrs,
                    src.width,
                    src.height,
                    *src.bounds,
                    dst_width=right - left,
                    dst_height=top - bottom,
                )

                # extract the profile of the destination file and update it with
                # first the creation parameter of a Gtiff file
                # then the features of the projected output
                profile = src.profile.copy()
                profile.update(
                    large_image.tilesource.base._rasterioParameters(
                        defaultCompression="lzw", **kwargs
                    )
                )
                profile.update(
                    width=right - left,
                    height=top - bottom,
                    transform=transform,
                    crs=dstCrs,
                )

                # reproject every band
                with rio.open(output.name, "w", **profile) as dst:
                    for i in range(src.count):
                        rio.warp.reproject(
                            source=rio.band(src, i + 1),
                            destination=rio.band(dst, i + 1),
                            src_crs=src.crs,
                            dst_crs=dstCrs,
                        )

        return pathlib.Path(output.name), TileOutputMimeTypes["TILED"]

    def getRegion(self, format_=(TILE_FORMAT_IMAGE,), **kwargs):
        """
        Get a rectangular region from the current tile source.  Aspect ratio is preserved.
        If neither width nor height is given, the original size of the highest
        resolution level is used.  If both are given, the returned image will be
        no larger than either size.

        :param format: the desired format or a tuple of allowed formats. Formats
            are members of (TILE_FORMAT_PIL, TILE_FORMAT_NUMPY, TILE_FORMAT_IMAGE).
            If TILE_FORMAT_IMAGE, encoding may be specified.
        :param kwargs: optional arguments.  Some options are region, output, encoding,
            jpegQuality, jpegSubsampling, tiffCompression, fill.  See tileIterator.

        :returns: regionData, formatOrRegionMime: the image data and either the
            mime type, if the format is TILE_FORMAT_IMAGE, or the format.
        """

        # cast format as a tuple if needed
        format_ = format_ if isinstance(format_, (tuple, set, list)) else (format_,)

        # The tile iterator handles determining the output region
        iterInfo = self._tileIteratorInfo(**kwargs)

        # gdal warp is not required if the original region has be istyled
        if not (
            iterInfo
            and not self._jsonstyle
            and TILE_FORMAT_IMAGE in format_
            and kwargs.get("encoding") == "TILED"
        ):
            return super().getRegion(format_, **kwargs)

        # extract parameter of the projection
        dstCrs = self.projection or self.getCrs()
        top = iterInfo["region"]["top"]
        left = iterInfo["region"]["left"]
        bottom = iterInfo["region"]["bottom"]
        right = iterInfo["region"]["right"]

        with self._getDatasetLock, tempfile.NamedTemporaryFile(
            suffix=".tiff", prefix="tiledGeoRegion_", delete=False
        ) as output:

            # compute the transformation
            transform, width, height = rio.warp.calculate_default_transform(
                self.dataset.crs,
                dstCrs,
                self.dataset.width,
                self.dataset.height,
                *self.dataset.bounds,
                dst_width=right - left,
                dst_height=top - bottom,
            )

            # extract the profile of the destination file and update it with
            # first the creation parameter of a Gtiff file
            # then the features of the projected output
            profile = self.dataset.profile.copy()
            profile.update(
                large_image.tilesource.base._rasterioParameters(
                    defaultCompression="lzw", **kwargs
                )
            )
            profile.update(
                width=right - left,
                height=top - bottom,
                transform=transform,
                crs=dstCrs,
            )

            # reproject every band
            with rio.open(output.name, "w", **profile) as dst:
                for i in range(self.dataset.count):
                    rio.warp.reproject(
                        source=rio.band(self.dataset, i + 1),
                        destination=rio.band(dst, i + 1),
                        src_crs=self.dataset.crs,
                        dst_crs=dstCrs,
                    )

            return pathlib.Path(output.name), TileOutputMimeTypes["TILED"]

    def validateCOG(self, strict=True, warn=True):
        """
        Check if this image is a valid Cloud Optimized GeoTiff.

        This will raise a :class:`large_image.exceptions.TileSourceInefficientError`
        if not a valid Cloud Optimized GeoTiff. Otherwise, returns True. Requires
        the ``rio-cogeo`` lib.


        :param strict: Enforce warnings as exceptions. Set to False to only warn
            and not raise exceptions.
        :param warn: Log any warnings

        :returns: the validity of the cogtiff
        """

        from rio_cogeo.cogeo import cog_validate

        isValid, errors, warnings = cog_validate(self._largeImagePath, strict=strict)

        if errors:
            raise TileSourceInefficientError(errors)
        if strict and warnings:
            raise TileSourceInefficientError(warnings)
        if warn:
            for warning in warnings:
                self.logger.warning(warning)

        return isValid


def open(*args, **kwargs):
    """
    Create an instance of the module class.
    """

    return RasterioFileTileSource(*args, **kwargs)


def canRead(*args, **kwargs):
    """
    Check if an input can be read by the module class.
    """

    return RasterioFileTileSource.canRead(*args, **kwargs)
