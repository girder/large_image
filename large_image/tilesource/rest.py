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

import tornado.httpserver
import tornado.netutil
import tornado.web

from large_image.exceptions import TileSourceXYZRangeError


def launch_tile_server(tile_source, port=0):

    class TileSourceMetadataHandler(tornado.web.RequestHandler):
        """REST endpoint to get image metadata."""

        def get(self):
            self.write(json.dumps(tile_source.getMetadata()))
            self.set_header("Content-Type", "application/json")

    class TileSourceTileHandler(tornado.web.RequestHandler):
        """REST endpoint to server tiles from image in slippy maps standard."""

        def get(self):
            x = int(self.get_argument("x"))
            y = int(self.get_argument("y"))
            z = int(self.get_argument("z"))
            encoding = self.get_argument("encoding", "PNG")
            try:
                tile_binary = tile_source.getTile(x, y, z, encoding=encoding)
            except TileSourceXYZRangeError as e:
                self.clear()
                self.set_status(404)
                self.finish(f"<html><body>{e}</body></html>")
            else:
                self.write(tile_binary)
                self.set_header("Content-Type", "image/png")

    app = tornado.web.Application([
        (r"/metadata", TileSourceMetadataHandler),
        (r"/tile", TileSourceTileHandler),
    ])
    sockets = tornado.netutil.bind_sockets(port, '')
    server = tornado.httpserver.HTTPServer(app)
    server.add_sockets(sockets)

    # Return ports
    return tuple(s.getsockname()[1] for s in sockets)
