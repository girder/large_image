import large_image
import pytest
import urllib


@pytest.mark.parametrize("file_, output", [
    ('57b345d28d777f126827dc27', '/tmp/sample_jp2k.svs'),
    ('57b345d28d777f126827dc28', '/tmp/sample_svs_imamge.svs')
])
def test_tiff_tile_source(file_, output):
    """Check whether large_image can return a tile with svs sources."""
    test_url = 'https://data.kitware.com/api/v1/file/{}/download'.format(file_)
    urllib.urlretrieve(test_url, output)
    image = large_image.getTileSource(output)
    # Make sure it is the svs tile source
    assert isinstance(image, large_image.tilesource.SVSFileTileSource)
    # Make sure we can get a tile without an exception
    assert type(image.getTile(0, 0, 0)) == str
