import pooch
from pathlib import Path

EXAMPLES_FOLDER = Path('format_examples')

format_examples = [
    dict(
        name='TIFF',
        extensions=['tiff', 'tif', 'ptif', 'ptiff', 'qptiff'],
        long_name='Tagged Image File Format',
        reference='https://www.itu.int/itudoc/itu-t/com16/tiff-fx/docs/tiff6.pdf',
        examples=[
            dict(
                filename='tcgaextract_ihergb_labeled.tiff',
                url='https://data.kitware.com/api/v1/item/66e30827560e6127967912cf/download',
                hash='8a03ae4370a35517e2ab2249177d903c1ea52869e30dc558750c626d9edbae6f',
            ),
        ],
    ),
    dict(
        name='SVS',
        extensions=['svs', 'svslide'],
        long_name='Aperio ScanScope Virtual Slide',
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
        name='OME-TIFF',
        extensions=['ome.tiff', 'ome.tif', 'ome'],
        long_name='Open Microscopy Environment Tagged Image File Format',
        reference='https://docs.openmicroscopy.org/ome-model/5.6.3/ome-tiff/',
        examples=[
            dict(
                filename='DDX58_AXL_EGFR_well2_XY04.ome.tif',
                url='https://data.kitware.com/api/v1/file/5fa1cbe750a41e3d192e18eb/download',
                hash='5dabb19081db4893d58b6680e54b566fc6246ccbde10d41413201afd96499482',
            ),
        ],
    ),
    dict(
        name='NDPI',
        extensions=['ndpi', 'ndpis'],
        long_name='Hamamatsu NanoZoomer Digital Pathology Image',
        reference='https://openslide.org/formats/hamamatsu/',
        examples=[
            dict(
                filename='test3.ndpis',
                url='https://data.kitware.com/api/v1/item/66e1af68560e612796791287/download',
                hash='35542dff44d7844f1fac04c1703bdb1476f90f484457907ead132203e6de066e',
            ),
            dict(
                filename='test3-TRITC 2 (560).ndpi',
                url='https://data.kitware.com/api/v1/item/66e1af63560e61279679127e/download',
                skip=True,
                hash='f02985d30aa38060e83c9477a4435cb81b2a0a234d3d664195dfc5a4e2657be8',
            ),
            dict(
                filename='test3-FITC 2 (485).ndpi',
                url='https://data.kitware.com/api/v1/item/66e1af65560e612796791281/download',
                skip=True,
                hash='455069a02a761ecfedb93492f103dec8c5b23b7c46fd47e9d8d22191ea803018',
            ),
            dict(
                filename='test3-DAPI 2 (387).ndpi',
                url='https://data.kitware.com/api/v1/item/66e1af68560e612796791284/download',
                skip=True,
                hash='9294d31f304f20ef1df1e08650d3f225b8ed44db8b2dc0d52f584449f85bdca2',
            ),
        ],
    ),
    dict(
        name='Zarr',
        extensions=['zarr', 'zarray', 'zattrs', 'zgroup', 'zip', 'db', 'sqlite'],
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
        name='ND2',
        extensions=['nd2'],
        long_name='Nikon NIS Elements',
        reference='https://docs.openmicroscopy.org/bio-formats/5.9.2/formats/nikon-nis-elements-nd2.html',
        examples=[
            dict(
                filename='sample_image.nd2',
                # originally from 'https://downloads.openmicroscopy.org/images/ND2/aryeh/MeOh_high_fluo_003.nd2',
                url='https://data.kitware.com/api/v1/item/66fde0be2480d44510d0ca24/download',
                hash='8e23bb594cd18314f9c18e70d736088ae46f8bc696ab7dc047784be416d7a706',
            ),
        ],
    ),
    dict(
        name='CZI',
        extensions=['czi'],
        long_name='Carl Zeiss Image',
        reference='https://www.zeiss.com/microscopy/en/products/software/zeiss-zen/czi-image-file-format.html',
        examples=[
            dict(
                filename='Plate1-Blue-A-02-Scene-1-P2-E1-01.czi',
                url='https://data.kitware.com/api/v1/item/66e1af4d560e61279679127b/download',
                hash='494936fa5a8c2e53b73672980986e2c44f3779e9b709ebfd406ffda723336376',
            ),
        ],
    ),
    dict(
        name='DICOM',
        extensions=['dcm', 'dic', 'dicom'],
        long_name='Digital Imaging and Communications in Medicine',
        reference='https://www.dicomstandard.org/about',
        examples=[
            dict(
                filename='US-MONO2-8-8x-execho.dcm',
                # originally from 'https://downloads.openmicroscopy.org/images/DICOM/samples/US-MONO2-8-8x-execho.dcm',
                url='https://data.kitware.com/api/v1/item/66fde1732480d44510d0ca27/download',
                hash='7d3f54806d0315c6cfc8b7371649a242b5ef8f31e0d20221971dd8087f2ff1ea',
            ),
        ],
    ),
    dict(
        name='LIF',
        extensions=['lif', 'liff'],
        long_name='Leica Image Format',
        reference='https://svi.nl/LeicaLif',
        examples=[
            dict(
                filename='20191025 Test FRET 585. 423, 426.lif',
                # originally from 'https://downloads.openmicroscopy.org/images/Leica-LIF/imagesc-30856/20191025%20Test%20FRET%20585.%20423,%20426.lif',
                url='https://data.kitware.com/api/v1/item/66fde1b82480d44510d0ca2a/download',
                hash='8d4ee62868b9616b832c2eb28e7d62ec050fb032e0bc11ea0a392f5c84390c71',
            ),
        ],
    ),
    dict(
        name='PNG',
        extensions=['png'],
        long_name='Portable Network Graphics',
        reference='http://www.libpng.org/pub/png/spec/1.2/PNG-Structure.html',
        examples=[
            dict(
                filename='Animated_PNG_example_bouncing_beach_ball.png',
                # originally from 'https://upload.wikimedia.org/wikipedia/commons/1/14/Animated_PNG_example_bouncing_beach_ball.png',
                url='https://data.kitware.com/api/v1/item/66fea4692480d44510d0ca6b/download',
                hash='3b28e2462f1b31d0d15d795e6e58baf397899c3f864be7034bf47939b5bbbc3b',
            ),
        ],
    ),
    dict(
        name='JPEG',
        extensions=['jpeg', 'jpe', 'jpg'],
        long_name='Joint Photographic Experts Group',
        reference='https://jpeg.org/jpeg/',
        examples=[
            dict(
                filename='albania.jpg',
                url='https://github.com/OSGeo/gdal/blob/master/autotest/gdrivers/data/jpeg/albania.jpg',
            ),
            dict(
                filename='clouds.jpeg',
                url='https://data.kitware.com/api/v1/file/5afd936c8d777f15ebe1b4d4/download',
                hash='fb195bb9dae13aa85d9f46f86ab9441a3b436dabbf57c68149453cba691d4391',
            ),
        ],
    ),
    dict(
        name='JPEG 2000',
        extensions=['j2c', 'j2k', 'jp2', 'jpf', 'jpx'],
        long_name='Joint Photographic Experts Group 2000',
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
        name='GIF',
        extensions=['gif'],
        long_name='Graphics Interchange Format',
        reference='https://www.adobe.com/creativecloud/file-types/image/raster/gif-file.html',
        examples=[
            dict(
                filename='SampleGIFImage_40kbmb.gif',
                # originally from 'https://sample-videos.com/gif/3.gif',
                url='https://data.kitware.com/api/v1/item/66fde6b52480d44510d0ca2d/download',
                hash='0ff064ba36e4f493f6a1b3d9d29c8eee1b719e39fc6768c5a6129534869c380b',
            ),
        ],
    ),
    dict(
        name='Bitmap',
        extensions=['bmp'],
        reference='https://www.ece.ualberta.ca/~elliott/ee552/studentAppNotes/2003_w/misc/bmp_file_format/bmp_file_format.htm',
        examples=[
            dict(
                filename='1bit.bmp',
                url='https://github.com/OSGeo/gdal/raw/master/autotest/gcore/data/1bit.bmp',
                hash='b0c201bee1e5a36ee698ab098aa3480e20772869d8f5c788280e532fa3620667',
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
