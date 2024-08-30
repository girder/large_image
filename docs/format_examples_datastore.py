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
