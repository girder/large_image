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
import os

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
    """Mixin class to support interactive visualization in Jupyter.

    This class implements ``_ipython_display_`` with ``ipyleaflet``
    to display an interactive image visualizer for the tile source
    in Jupyter-based environments.

    Install `ipyleaflet <https://github.com/jupyter-widgets/ipyleaflet>`_
    to interactively visualize tile sources in Jupyter.

    For remote JupyterHub environments, you may need to configure
    the class variables ``JUPYTER_HOST`` or ``JUPYTER_PROXY``.

    If ``JUPYTER_PROXY`` is set, it overrides ``JUPYTER_HOST``.

    Use ``JUPYTER_HOST`` to set the host name of the machine such
    that the tile URL can be accessed at
    ``'http://{JUPYTER_HOST}:{port}'``.

    Use ``JUPYTER_PROXY`` to leverage ``jupyter-server-proxy`` to
    proxy the tile serving port through Jupyter's authenticated web
    interface. This is useful in Docker and cloud JupyterHub
    environments. You can set the environment variable
    ``LARGE_IMAGE_JUPYTER_PROXY`` to control the default value of
    ``JUPYTER_PROXY``. If ``JUPYTER_PROXY`` is set to ``True``, the
    default will be ``'/proxy/`` which will work for most Docker
    Jupyter configurations. If in a cloud JupyterHub environment,
    this will get a bit more nuanced as the
    ``JUPYTERHUB_SERVICE_PREFIX`` may need to prefix the
    ``'/proxy/'``.

    To programatically set these values:

    .. code::

        from large_image.tilesource.jupyter import IPyLeafletMixin

        # Only set one of these values

        # Use a custom domain (avoids port proxying)
        IPyLeafletMixin.JUPYTER_HOST = 'mydomain'

        # Proxy in a standard JupyterLab environment
        IPyLeafletMixin.JUPYTER_PROXY = True  # defaults to `/proxy/`

        # Proxy in a cloud JupyterHub environment
        IPyLeafletMixin.JUPYTER_PROXY = '/jupyter/user/username/proxy/'
        # See if ``JUPYTERHUB_SERVICE_PREFIX`` is in the environment
        # variables to improve this

    """

    JUPYTER_HOST = '127.0.0.1'
    JUPYTER_PROXY = os.environ.get('LARGE_IMAGE_JUPYTER_PROXY', False)

    def __init__(self, *args, **kwargs):
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
                base_url = f'{self.JUPYTER_PROXY.rstrip("/")}/{self._ports[0]}'
            else:
                base_url = f'/proxy/{self._ports[0]}'
        else:
            base_url = f'http://{self.JUPYTER_HOST}:{self._ports[0]}'

        # Use repr in URL params to prevent caching across sources/styles
        endpoint = f'tile?z={{z}}&x={{x}}&y={{y}}&encoding=png&repr={self.__repr__()}'

        layer = TileLayer(
            url=f'{base_url}/{endpoint}',
            # attribution='Tiles served with large-image',
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

            geospatial = self.geospatial and self.projection

            if geospatial:
                # TODO: better handle other projections
                crs = projections.EPSG3857
            else:
                crs = dict(
                    name='PixelSpace',
                    custom=True,
                    # Why does this need to be 256?
                    resolutions=[256 * 2 ** (-l) for l in range(20)],

                    # This works but has x and y reversed
                    proj4def='+proj=longlat +axis=esu',
                    bounds=[[0, 0], [metadata['sizeY'], metadata['sizeX']]],
                    origin=[0, 0],

                    # This almost works to fix the x, y reversal, but
                    # - bounds are weird and other issues occur
                    # proj4def='+proj=longlat +axis=seu',
                    # bounds=[[-metadata['sizeX'],-metadata['sizeY']],[metadata['sizeX'],metadata['sizeY']]],
                    # origin=[0,0],
                )

            m = Map(
                crs=crs,
                basemap=basemaps.OpenStreetMap.Mapnik if geospatial else t,
                center=self.getCenter(srs='EPSG:4326'),
                zoom=default_zoom,
                max_zoom=metadata['levels'] + 1,
                min_zoom=0,
                scroll_wheel_zoom=True,
                dragging=True,
                # attribution_control=False,
            )
            if geospatial:
                m.add_layer(t)
            return display(m)
