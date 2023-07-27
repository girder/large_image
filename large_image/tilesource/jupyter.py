"""A vanilla REST interface to a ``TileSource``.

This is intended for use in JupyterLab and not intended to be used as a full
fledged REST API. Only two endpoints are exposed with minimal options:

* `/metadata`
* `/tile?z={z}&x={x}&y={y}&encoding=png`

We use Tornado because it is Jupyter's web server and will not require Jupyter
users to install any additional dependencies. Also, Tornado doesn't require us
to manage a separate thread for the web server.

Please note that this webserver will not work with Classic Notebook and will
likely lead to crashes. This is only for use in JupyterLab.

"""
import json
import os
import weakref

from large_image.exceptions import TileSourceXYZRangeError

try:
    import ipyleaflet
except ImportError:  # pragma: no cover
    ipyleaflet = None


def launch_tile_server(tile_source, port=0):
    import tornado.httpserver
    import tornado.netutil
    import tornado.web

    class RequestManager:
        def __init__(self, tile_source):
            self._tile_source_ = weakref.ref(tile_source)
            self._ports = ()

        @property
        def tile_source(self):
            return self._tile_source_()

        @tile_source.setter
        def tile_source(self, source):
            self._tile_source_ = weakref.ref(source)

        @property
        def ports(self):
            return self._ports

        @property
        def port(self):
            return self.ports[0]

    manager = RequestManager(tile_source)
    # NOTE: set `ports` manually after launching server

    class TileSourceMetadataHandler(tornado.web.RequestHandler):
        """REST endpoint to get image metadata."""

        def get(self):
            self.write(json.dumps(manager.tile_source.getMetadata()))
            self.set_header('Content-Type', 'application/json')

    class TileSourceTileHandler(tornado.web.RequestHandler):
        """REST endpoint to serve tiles from image in slippy maps standard."""

        def get(self):
            x = int(self.get_argument('x'))
            y = int(self.get_argument('y'))
            z = int(self.get_argument('z'))
            encoding = self.get_argument('encoding', 'PNG')
            try:
                tile_binary = manager.tile_source.getTile(x, y, z, encoding=encoding)
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

    manager._ports = tuple(s.getsockname()[1] for s in sockets)
    return manager


class IPyLeafletMixin:
    """Mixin class to support interactive visualization in JupyterLab.

    This class implements ``_ipython_display_`` with ``ipyleaflet``
    to display an interactive image visualizer for the tile source
    in JupyterLab.

    Install `ipyleaflet <https://github.com/jupyter-widgets/ipyleaflet>`_
    to interactively visualize tile sources in JupyterLab.

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

    To programmatically set these values:

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
        self._jupyter_server_manager = None

    def as_leaflet_layer(self, **kwargs):
        # NOTE: `as_leaflet_layer` is supported by ipyleaflet.Map.add
        from ipyleaflet import TileLayer

        if self._jupyter_server_manager is None:
            # Must relaunch to ensure style updates work
            self._jupyter_server_manager = launch_tile_server(self)
        else:
            # Must update the source on the manager in case the previous reference is bad
            self._jupyter_server_manager.tile_source = self

        port = self._jupyter_server_manager.port

        metadata = self.getMetadata()

        if self.JUPYTER_PROXY:
            if isinstance(self.JUPYTER_PROXY, str):
                base_url = f'{self.JUPYTER_PROXY.rstrip("/")}/{port}'
            else:
                base_url = f'/proxy/{port}'
        else:
            base_url = f'http://{self.JUPYTER_HOST}:{port}'

        # Use repr in URL params to prevent caching across sources/styles
        endpoint = f'tile?z={{z}}&x={{x}}&y={{y}}&encoding=png&repr={self.__repr__()}'

        if not (self.geospatial and self.projection) and 'bounds' not in kwargs:
            kwargs = kwargs.copy()
            kwargs['bounds'] = [[0, 0], [metadata['sizeY'], metadata['sizeX']]]
        layer = TileLayer(
            url=f'{base_url}/{endpoint}',
            # attribution='Tiles served with large-image',
            min_zoom=0,
            max_native_zoom=metadata['levels'],
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

            t = self.as_leaflet_layer()

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
                    resolutions=[2 ** (metadata['levels'] - 1 - l) for l in range(20)],

                    # This works but has x and y reversed
                    proj4def='+proj=longlat +axis=esu',
                    bounds=[[0, 0], [metadata['sizeY'], metadata['sizeX']]],
                    # Why is origin X, Y but bounds Y, X?
                    origin=[0, metadata['sizeY']],

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
