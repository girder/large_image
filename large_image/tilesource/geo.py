from urllib.parse import urlencode, urlparse

from .base import FileTileSource


def make_vsi(url: str, **options):
    if str(url).startswith("s3://"):
        s3_path = url.replace("s3://", "")
        vsi = f"/vsis3/{s3_path}"
    else:
        gdal_options = {
            "url": str(url),
            "use_head": "no",
            "list_dir": "no",
        }
        gdal_options.update(options)
        vsi = f"/vsicurl?{urlencode(gdal_options)}"
    return vsi


class GeoFileTileSource(FileTileSource):
    """Abstract base class for geospatial tile sources.

    This base class assumes the underlying library is powered by GDAL
    (rasterio, mapnik, etc.)
    """

    geospatial = True

    def _getLargeImagePath(self):
        """Get GDAL-compatible image path.

        This will cast the output to a string and can also handle URLs
        ('http', 'https', 'ftp', 's3') for use with GDAL
        `Virtual Filesystems Interface <https://gdal.org/user/virtual_file_systems.html>`_.
        """
        if urlparse(str(self.largeImagePath)).scheme in {"http", "https", "ftp", "s3"}:
            return make_vsi(self.largeImagePath)
        return str(self.largeImagePath)
