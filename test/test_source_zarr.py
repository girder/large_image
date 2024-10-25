import large_image_source_zarr

from .datastore import datastore


def testZarrAxisOrder():
    imagePath = datastore.fetch('synthetic_multiaxis.zarr.db')
    source = large_image_source_zarr.open(imagePath)
    assert source.metadata['IndexStride']['IndexC'] == 1
