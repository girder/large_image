# Using Large Image in Jupyter

The large_image library has some convenience features for use in Jupyter Notebooks and Jupyter Lab. Different features are available depending on whether your data files are local or on a Girder server.

## Installation

The large_image library has a variety of tile sources to support a wide range of file formats. Many of these depend on binary libraries. For linux systems, you can install these from python wheels via the `--find-links` option. For other operating systems, you will need to install different libraries depending on what tile sources you wish to use.

## Using Local Files

When using large_image with local files, when you open a file, large_image returns a tile source. See [girder.github.io/large_image](https://girder.github.io/large_image) for documentation on what you can do with this.

First, we download a few files so we can use them locally.

## Basic Use

The large_image library has a variety of tile sources that support a wide range of formats. In general, you don’t need to know the format of a file, you can just open it.

Every file has a common interface regardless of its format. The metadata gives a common summary of the data.

If you have ipyleaflet installed and are using JupyterLab, you can ask the system to proxy requests to an internal tile server that allows you to view the image in a zoomable viewer. There are more options depending on your Jupyter configuration and whether it is running locally or remotely.
<br/>
Some environments need different proxy options, like Google CoLab. The system will attempt to determine the correct proxy values by default. If you needed to, you could ask JupyterLab to locally proxy an internal tile server. As an example:
<br/>

`large_image.tilesource.jupyter.IPyLeafletMixin.JUPYTER_PROXY = True`

If ipyleaflet isn’t installed, inspecting a tile source will just show the thumbnail.

By default in the Jupyter notebook environment, images are opened with PNG encoding so that areas outside the image bounds are transparent. You may chose to specify a different encoding when opening the image. Applicable options include ‘JPEG’, ‘PNG’, ‘TIFF’, and ‘TILED’. Opening this image with ‘JPEG’ encoding may result in black borders outside of the image bounds.

The IPyLeaflet map uses a bottom-up y, x coordinate system, not the top-down x, y coordinate system most image system use. The rationale is that this is appropriate for geospatial maps with latitude and longitude, but it doesn’t carry over to pixel coordinates very well. There are some convenience functions to convert coordinates.

## Geospatial Sources

For geospatial sources, the default viewer shows the image in context on a world map. By default in the Jupyter notebook environment, geospatial images are opened with a projection of ‘EPSG:3857’.

To view the image in pixel coordinates without the map layer below, open the file with a projection of None.

Geospatial sources have additional metadata and thumbnails.

To get a specific region of a geospatial image, you can specify region bounds with projection coordinates. The projection is passed to the region’s `units` argument as a string. If `units` is `'projection'`, the source’s default projection will be used. If `units` starts with `'proj4:'` or `'epsg:'` (case-insensitive), the projection interpreted from that string will be used. In the following example, we use `'EPSG:4326'` and specify the region with latitude and longitude values.

You can also specify a region with a single corner point and distances for width and height:

## Girder Server Sources

You can use files on a Girder server by just download them and using them locally. However, you can use girder client to access files more conveniently. If the Girder server doesn’t have the large_image plugin installed on it, this can still be useful – functionally, this pulls the file and provides a local tile server, so some of this requires the same proxy setup as a local file.

`large_image.tilesource.jupyter.Map` is a convenience class that can use a variety of remote sources.

**(1)** We can get a source from girder via item or file id

**(2)** We could use a resource path instead of an id

**(3)** We can use a girder server that has the large_image plugin enabled. This lets us do more than just look at the image.

We can get data as a numpy array.

**(4)** From a metadata dictionary and a url. Any slippy-map style tile server could be used.
