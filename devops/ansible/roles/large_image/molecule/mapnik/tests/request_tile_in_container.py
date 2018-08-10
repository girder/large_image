import large_image
import urllib
import pytest


@pytest.mark.parametrize("test_url, output", [
    ('https://download.osgeo.org/geotiff/samples/spot/chicago/SP27GTIF.TIF',
     '/tmp/chicago.tif')
])
def test_mapnik_tile_source(test_url, output):
    """Check whether large_image can return a tile with mapnik sources."""
    urllib.urlretrieve(test_url, output)
    image = large_image.getTileSource(output)
    metadata = image.getMetadata()
    # Make sure it is the mapnik tile source
    assert metadata['geospatial']
    assert metadata['bounds']
    assert isinstance(image, large_image.tilesource.MapnikTileSource)
    # Make sure we can get a tile without an exception
    assert type(image.getTile(0, 0, 0)) == str
