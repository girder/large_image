"""A vanilla REST interface to a ``TileSource``.

This is intended for use in Jupyter and not intended to be used as a full
fledged REST API. Only two endpoints are exposed with minimal options:

* `/metadata`
* `/tile?z={z}&x={x}&y={y}&encoding=png`

We use Tornado because it is Jupyter's web server and will not require Jupyter
users to install any additional dependencies. Also, Tornado doesn't require us
to manage a seperate thread for the web server.

"""
import json

from large_image.exceptions import TileSourceXYZRangeError

try:
    import ipyleaflet
except ImportError:  # pragma: no cover
    ipyleaflet = None


def launch_tile_server(tile_source, port=0):
    import tornado.httpserver
    import tornado.netutil
    import tornado.web

    class TileSourceMetadataHandler(tornado.web.RequestHandler):
        """REST endpoint to get image metadata."""

        def get(self):
            self.write(json.dumps(tile_source.getMetadata()))
            self.set_header('Content-Type', 'application/json')

    class TileSourceTileHandler(tornado.web.RequestHandler):
        """REST endpoint to server tiles from image in slippy maps standard."""

        def get(self):
            x = int(self.get_argument('x'))
            y = int(self.get_argument('y'))
            z = int(self.get_argument('z'))
            encoding = self.get_argument('encoding', 'PNG')
            try:
                tile_binary = tile_source.getTile(x, y, z, encoding=encoding)
            except TileSourceXYZRangeError as e:
                self.clear()
                self.set_status(404)
                self.finish(f'<html><body>{e}</body></html>')
            else:
                self.write(tile_binary)
                self.set_header('Content-Type', 'image/png')

    app = tornado.web.Application([
        (r'/metadata', TileSourceMetadataHandler),
        (r'/tile', TileSourceTileHandler),
    ])
    sockets = tornado.netutil.bind_sockets(port, '')
    server = tornado.httpserver.HTTPServer(app)
    server.add_sockets(sockets)

    # Return ports
    return tuple(s.getsockname()[1] for s in sockets)


class IPyLeafletMixin:

    JUPYTER_HOST = '127.0.0.1'
    JUPYTER_PROXY = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # launch_tile_server ports
        self._ports = ()

    def getIpyleafletTileLayer(self, **kwargs):
        from ipyleaflet import TileLayer

        if not self._ports:
            # TODO: destroy previous server
            ...
        # Always relaunch the server
        # - otherwise, styling changes won't take affect
        self._ports = launch_tile_server(self)

        metadata = self.getMetadata()

        if self.JUPYTER_PROXY:
            if isinstance(self.JUPYTER_PROXY, str):
                base_url = f'{self.JUPYTER_PROXY}/{self._ports[0]}'
            else:
                base_url = f'/proxy/{self._ports[0]}'
        else:
            base_url = f'http://{self.JUPYTER_HOST}:{self._ports[0]}'

        # Use repr in URL params to prevent caching across sources/styles
        endpoint = f'tile?z={{z}}&x={{x}}&y={{y}}&encoding=png&repr={self.__repr__()}'

        layer = TileLayer(
            url=f"{base_url}/{endpoint}",
            # attribution="Tiles served with large-image",
            min_zoom=0,
            max_native_zoom=metadata['levels'] + 1,
            max_zoom=20,
            tile_size=metadata['tileWidth'],
            **kwargs,
        )
        return layer

    # Only make _ipython_display_ available if ipyleaflet is installed
    if ipyleaflet:

        def _ipython_display_(self):
            from ipyleaflet import Map, basemaps, projections
            from IPython.display import display

            metadata = self.getMetadata()

            t = self.getIpyleafletTileLayer()

            try:
                default_zoom = metadata['levels'] - metadata['sourceLevels']
            except KeyError:
                default_zoom = 0

            proj = dict(
                name='PixelSpace',
                custom=True,
                # Why does this need to be 256?
                resolutions=[256 * 2 ** (-l) for l in range(20)],

                # This works but has x and y reversed
                proj4def='+proj=longlat +axis=esu',
                bounds=[[0, 0], [metadata['sizeY'], metadata['sizeX']]],
                origin=[0, 0],

                # This almost works to fix the x, y reversal, but bounds are weird and other issues occur
                # proj4def='+proj=longlat +axis=seu',
                # bounds=[[-metadata['sizeX'],-metadata['sizeY']],[metadata['sizeX'],metadata['sizeY']]],
                # origin=[0,0],
            )

            m = Map(
                crs=projections.EPSG3857 if self.geospatial else proj,
                basemap=basemaps.OpenStreetMap.Mapnik if self.geospatial else t,
                center=self.getCenter(srs='EPSG:4326'),
                zoom=default_zoom,
                max_zoom=metadata['levels'] + 1,
                min_zoom=0,
                scroll_wheel_zoom=True,
                dragging=True,
                # attribution_control=False,
            )
            if self.geospatial:
                m.add_layer(t)
            return display(m)
