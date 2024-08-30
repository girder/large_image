import pooch
from pathlib import Path

EXAMPLES_FOLDER = Path('format_examples')

format_examples = [
    dict(
        name='TIFF (Tagged Image File Format)',
        reference='https://www.itu.int/itudoc/itu-t/com16/tiff-fx/docs/tiff6.pdf',
        examples=[
            dict(
                filename='utmsmall.tif',
                url='https://github.com/OSGeo/gdal/raw/master/autotest/gcore/data/utmsmall.tif',
                hash='f40dae6e8b5e18f3648e9f095e22a0d7027014bb463418d32f732c3756d8c54f',
            ),
            dict(
                filename='tcgaextract_rgb.tiff',
                url='https://data.kitware.com/api/v1/file/649d939c5121da8eb1a81454/download',
                hash='3cd5e1ebde5127bafebd9432e10b2c47d9035fb4242bd6e5e941389d2b23ec1e',
            ),
            dict(
                filename='sample_image.ptif',
                url='https://data.kitware.com/api/v1/file/5be43e398d777f217991e21f/download',
                hash='d73cbf87aac8f9cd9544b20d6c42537f4c609da15817928c8824d57049a2749a',
            ),
        ],
    ),
    dict(
        name='Zarr',
        reference='https://wiki.earthdata.nasa.gov/display/ESO/Zarr+Format',
        examples=[
            dict(
                filename='WD1.1_17-03_WT_MP.ome.zarr.zip',
                url='https://data.kitware.com/api/v1/file/6544e995fdc1508d8bec1838/download',
                hash='f7dfb6683107d1cb21a360e31752b02641a16e0d32a87698669838418f108831',
            ),
            dict(
                filename='normmedia_8well_col2_livecellgfp.db',
                url='https://data.kitware.com/api/v1/file/6544e9f5fdc1508d8bec1860/download',
                hash='7d6cfb6967f79eb5201eebbe93418e26445676d9ea95a3bf49ff4ffbf0993e39',
            ),
        ],
    ),
    dict(
        name='PNG (Portable Network Graphics)',
        reference='http://www.libpng.org/pub/png/spec/1.2/PNG-Structure.html',
        examples=[
            dict(
                filename='test.png',
                url='https://github.com/OSGeo/gdal/raw/master/autotest/gdrivers/data/png/test.png',
                hash='16cd80a28a70e0f71a6316fd8e3c679da2a2bf62bec913718c8063aff0e4a625',
            ),
        ],
    ),
    dict(
        name='JPEG (Joint Photographic Experts Group)',
        reference='https://jpeg.org/jpeg/',
        examples=[
            dict(
                filename='albania.jpg',
                url='https://github.com/OSGeo/gdal/blob/master/autotest/gdrivers/data/jpeg/albania.jpg',
                hash='c454c477056b26cceb5461648f825efdf9362c7b7998a4a0ca41050629e692de',
            ),
            dict(
                filename='clouds.jpeg',
                url='https://data.kitware.com/api/v1/file/5afd936c8d777f15ebe1b4d4/download',
                hash='fb195bb9dae13aa85d9f46f86ab9441a3b436dabbf57c68149453cba691d4391',
            ),
        ],
    ),
    dict(
        name='JPEG (Joint Photgraphic Experts Group) 2000',
        reference='https://jpeg.org/jpeg2000/index.html',
        examples=[
            dict(
                filename='erdas_foo.jp2',
                url='https://github.com/OSGeo/gdal/raw/master/autotest/gdrivers/data/jpeg2000/erdas_foo.jp2',
                hash='d08653919c41a49cd31f9116278fe6a6d8c189dc6379a280810f65df11bde006',
            ),
        ],
    ),
    dict(
        name='GIF (Graphics Interchange Format)',
        reference='https://www.adobe.com/creativecloud/file-types/image/raster/gif-file.html',
        examples=[
            dict(
                filename='sample_640×426.gif',
                url='https://filesamples.com/samples/image/gif/sample_640%C3%97426.gif',
                hash='eb04e3ff38fc7ecba1f7715ca7dae26b24e03766dc7c43ddeec75d5f1af74acd',
            ),
        ],
    ),
    dict(
        name='Bitmap',
        reference='https://www.ece.ualberta.ca/~elliott/ee552/studentAppNotes/2003_w/misc/bmp_file_format/bmp_file_format.htm',
        examples=[
            dict(
                filename='1bit.bmp',
                url='https://github.com/OSGeo/gdal/raw/master/autotest/gcore/data/1bit.bmp',
                hash='b0c201bee1e5a36ee698ab098aa3480e20772869d8f5c788280e532fa3620667',
            ),
        ],
    ),
    dict(
        name='LIF (Leica Image Format)',
        reference='https://svi.nl/LeicaLif',
        examples=[
            dict(
                filename='20191025 Test FRET 585. 423, 426.lif',
                url='https://downloads.openmicroscopy.org/images/Leica-LIF/imagesc-30856/20191025%20Test%20FRET%20585.%20423,%20426.lif',
                hash='8d4ee62868b9616b832c2eb28e7d62ec050fb032e0bc11ea0a392f5c84390c71',
            ),
        ],
    ),
    dict(
        name='CZI (Carl Zeiss Image)',
        reference='https://www.zeiss.com/microscopy/en/products/software/zeiss-zen/czi-image-file-format.html',
        examples=[
            dict(
                filename='2014_07_01__0017_pt2.czi',
                url='https://data.kitware.com/api/v1/file/56993f1f8d777f429eac914d/download',
                hash='37b71c49dd0f0cf9ed3cf36c526db9c66b4c31032f42f8c31239f1a560c02741',
            ),
        ],
    ),
    dict(
        name='SVS (Aperio ScanScope Virtual Slide)',
        reference='https://paulbourke.net/dataformats/svs/',
        examples=[
            dict(
                filename='CMU-1.svs',
                url='https://data.kitware.com/api/v1/file/57b5d6558d777f10f2694486/download',
                hash='00a3d54482cd707abf254fe69dccc8d06b8ff757a1663f1290c23418c480eb30',
            ),
        ],
    ),
    dict(
        name='NDPI (Hamamatsu NanoZoomer Digital Pathology Image)',
        reference='https://openslide.org/formats/hamamatsu/',
        examples=[
            dict(
                filename='small2.ndpi',
                url='https://data.kitware.com/api/v1/file/5afd931e8d777f15ebe1b0f5/download',
                hash='4d66b72328b383dab7981e199f0251da01097d226cbe6023cfd7ee3c3cf5fec0',
            ),
        ],
    ),
    dict(
        name='OME-TIFF (Open Microscopy Environment Tagged Image File Format)',
        reference='https://docs.openmicroscopy.org/ome-model/5.6.3/ome-tiff/',
        examples=[
            dict(
                filename='DDX58_AXL_EGFR_well2_XY04.ome.tif',
                url='https://data.kitware.com/api/v1/file/5fa1cbe750a41e3d192e18eb/download',
                hash='5dabb19081db4893d58b6680e54b566fc6246ccbde10d41413201afd96499482',
            ),
        ],
    ),
]


def fetch_all():
    for format_data in format_examples:
        for example in format_data.get('examples', []):
            pooch.retrieve(
                url=example.get('url'),
                known_hash=example.get('hash'),
                fname=example.get('filename'),
                path=EXAMPLES_FOLDER,
            )
