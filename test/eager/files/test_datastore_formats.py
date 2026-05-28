import math

import numpy as np
import pytest

import large_image

from ...datastore import datastore

JAVA_RUNTIME_ERROR_TERMS = ('javahome', 'java -version', 'javabridge')


def open_datastore_source(filename):
    test_file = datastore.fetch(filename)
    try:
        return large_image.open(test_file)
    except Exception as exc:
        if any(term in str(exc) for term in JAVA_RUNTIME_ERROR_TERMS):
            pytest.skip(f'{filename} requires a working Java runtime for Bio-Formats')
        raise


def expected_base_tile_count(source):
    metadata = source.getMetadata()
    return (
        math.ceil(metadata['sizeX'] / metadata['tileWidth']) *
        math.ceil(metadata['sizeY'] / metadata['tileHeight'])
    )


@pytest.mark.skip(reason='Skipping because it is too slow')
@pytest.mark.singular
@pytest.mark.parametrize(
    'filename',
    [
        'synthetic_ndpi_2025.ndpi',
        'sample_image.ptif',
    ],
)
def test_eager_iterator_reads_all_base_pyramidal_tiles(filename):
    source = open_datastore_source(filename)
    expected_tiles = expected_base_tile_count(source)
    retrieved_tiles = 0

    iterator = source.eagerIterator(
        batch=64,
        prefetch=16,
        workers=16,
    )
    with iterator as eager_iterator:
        for batch in eager_iterator:
            shared_tiles = batch['tile']
            tiles = shared_tiles.view().copy()
            shared_tiles.close()

            assert batch['format'] == 'numpy'
            assert tiles.shape[1:] == (batch['height'], batch['width'], 3)
            assert tiles.dtype == np.uint8
            assert len(batch['gx']) == len(batch['gy']) == tiles.shape[0]
            assert len(batch['tile_position']['level_x']) == tiles.shape[0]
            assert len(batch['tile_position']['level_y']) == tiles.shape[0]

            retrieved_tiles += tiles.shape[0]

    del iterator

    assert retrieved_tiles == expected_tiles
