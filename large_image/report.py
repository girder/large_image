import scooby


class Report(scooby.Report):
    def __init__(self, additional=None, ncol=3, text_width=80, sort=False):
        """Initiate a scooby.Report instance."""

        # Mandatory packages.
        core = [
            'large_image',
            'cachetools',
            'PIL',
            'psutil',
            'numpy',
            'palettable',
            'scooby',
        ]

        girder = [
            'girder_large_image',
            'girder_worker_utils'
            'girder_worker'
        ]

        # Optional packages.
        sources = [
            'large_image_source_bioformats',
            'bioformats',
            'large_image_source_deepzoom',
            'large_image_source_dummy',
            'large_image_source_gdal',
            'osgeo.gdal',
            'pyproj',
            'large_image_source_mapnik',
            'mapnik',
            'large_image_source_nd2',
            'importlib',
            'nd2reader',
            'large_image_source_ometiff',
            'large_image_source_openjpeg',
            'glymur',
            'large_image_source_openslide',
            'openslide',
            'large_image_source_pil',
            'large_image_source_test',
            'large_image_source_tiff',
            'libtiff',
            'large_image_converter',
        ]

        optional = [
            'pylibmc',
            'matplotlib',
            'colorcet',
            'cmocean',
            'tifftools',
            'pyvips',
            'packaging',
            'skimage',
        ] + sources + girder

        scooby.Report.__init__(
            self,
            additional=additional,
            core=core,
            optional=optional,
            ncol=ncol,
            text_width=text_width,
            sort=sort,
        )
