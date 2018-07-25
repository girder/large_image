import large_image
import urllib


def test_pil_tile_source():
    """Check whether large_image can return a tile with pil source."""
    test_url = 'https://data.kitware.com/api/v1/item/590346fe8d777f16d01e0546/download'  # noqa: E501
    test_png = '/tmp/Easy1.png'
    urllib.urlretrieve(test_url, test_png)
    image = large_image.getTileSource(test_png)
    # Make sure it is the pil tile source
    assert isinstance(image, large_image.tilesource.PILFileTileSource)
    # Make sure we can get a tile without an exception
    assert type(image.getTile(0, 0, 0)) == str
