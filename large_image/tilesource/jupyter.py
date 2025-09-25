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
import ast
import asyncio
import importlib.util
import json
import os
import re
import threading
import time
import weakref
from typing import Any, Optional, Union, cast
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse

import numpy as np
import yaml

import large_image
from large_image.exceptions import TileSourceError, TileSourceXYZRangeError
from large_image.tilesource.utilities import JSONDict
from large_image.widgets.components import FrameSelector

ipyleafletPresent = importlib.util.find_spec('ipyleaflet') is not None
ipyvuePresent = importlib.util.find_spec('ipyvue') is not None
aiohttpPresent = importlib.util.find_spec('aiohttp') is not None

skimage_transform = None


def _lazyImportSkimageTransform():
    """
    Import the skimage.transform module. This is only needed when `editWarp=True` is used.
    """
    global skimage_transform

    if skimage_transform is None:
        try:
            import skimage.transform as skimage_transform
        except ImportError:
            msg = 'scikit-image transform module not found.'
            raise TileSourceError(msg)


class IPyLeafletMixin:
    """Mixin class to support interactive visualization in JupyterLab.

    This class implements ``_ipython_display_`` with ``ipyleaflet`` to display
    an interactive image visualizer for the tile source in JupyterLab.

    Install `ipyleaflet <https://github.com/jupyter-widgets/ipyleaflet>`_ to
    interactively visualize tile sources in JupyterLab.

    For remote JupyterHub environments, you may need to configure the class
    variables ``JUPYTER_HOST`` or ``JUPYTER_PROXY``.

    If ``JUPYTER_PROXY`` is set, it overrides ``JUPYTER_HOST``.

    Use ``JUPYTER_HOST`` to set the host name of the machine such that the tile
    URL can be accessed at ``'http://{JUPYTER_HOST}:{port}'``.

    Use ``JUPYTER_PROXY`` to leverage ``jupyter-server-proxy`` to proxy the
    tile serving port through Jupyter's authenticated web interface.  This is
    useful in Docker and cloud JupyterHub environments.  You can set the
    environment variable ``LARGE_IMAGE_JUPYTER_PROXY`` to control the default
    value of ``JUPYTER_PROXY``.  If ``JUPYTER_PROXY`` is set to ``True``, the
    default will be ``'/proxy/`` which will work for most Docker Jupyter
    configurations. If in a cloud JupyterHub environment, this will get a bit
    more nuanced as the ``JUPYTERHUB_SERVICE_PREFIX`` may need to prefix the
    ``'/proxy/'``.  If set to ``'auto'``, an automatic value will be chosen
    through some effort to detect the environment.

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
    JUPYTER_PROXY: Union[str, bool] = os.environ.get('LARGE_IMAGE_JUPYTER_PROXY', 'auto')

    _jupyter_server_manager: Any

    def __init__(self, *args, **kwargs) -> None:
        self._jupyter_server_manager = None
        self._map = Map(
            ts=self,
            editWarp=kwargs.get('editWarp', False),
            reference=kwargs.get('reference'),
        )
        if ipyleafletPresent:
            self.to_map = self._map.to_map
            self.from_map = self._map.from_map

    def as_leaflet_layer(self, **kwargs) -> Any:
        # NOTE: `as_leaflet_layer` is supported by ipyleaflet.Map.add

        if not getattr(self, '_noCache', False):
            msg = 'Cannot set the style of a cached source'
            raise TileSourceError(msg)

        if self._jupyter_server_manager is None:
            # Must relaunch to ensure style updates work
            self._jupyter_server_manager = launch_tile_server(self)
        else:
            # Must update the source on the manager in case the previous reference is bad
            self._jupyter_server_manager.tile_source = self

        port = self._jupyter_server_manager.port

        if self.JUPYTER_PROXY == 'auto':
            self._autoJupyterProxy()
        if self.JUPYTER_PROXY and str(self.JUPYTER_PROXY).lower() in {'true', 'false'}:
            self.JUPYTER_PROXY = str(self.JUPYTER_PROXY).lower() == 'true'
        if self.JUPYTER_PROXY:
            if isinstance(self.JUPYTER_PROXY, str):
                base_url = f'{self.JUPYTER_PROXY.rstrip("/")}/{port}'
            else:
                base_url = f'/proxy/{port}'
        else:
            base_url = f'http://{self.JUPYTER_HOST}:{port}'

        # Use repr in URL params to prevent caching across sources/styles
        endpoint = f'tile?z={{z}}&x={{x}}&y={{y}}&encoding=png&repr={self!r}'
        return self._map.make_layer(
            self.metadata,  # type: ignore[attr-defined]
            f'{base_url}/{endpoint}')

    def _autoJupyterProxy(self):
        if importlib.util.find_spec('google') and importlib.util.find_spec('google.colab'):
            # colab intercepts localhost
            self.JUPYTER_PROXY = 'https://localhost'
        elif importlib.util.find_spec('jupyter_server_proxy'):
            self.JUPYTER_PROXY = True
        else:
            self.JUPYTER_PROXY = False

    # Only make _ipython_display_ available if ipyleaflet is installed
    if ipyleafletPresent:

        def _ipython_display_(self) -> Any:
            from IPython.display import display

            t = self.as_leaflet_layer()

            return display(self._map.make_map(
                self.metadata, t, self.getCenter(srs='EPSG:4326')))  # type: ignore[attr-defined]

        @property
        def iplmap(self) -> Any:
            """
            If using ipyleaflets, get access to the map object.
            """
            return self._map.map

    @property
    def warp_points(self):
        return self._map.warp_points


class Map:
    """
    An IPyLeafletMap representation of a large image.
    """

    def __init__(
            self, *, ts: Optional[IPyLeafletMixin] = None,
            metadata: Optional[dict] = None, url: Optional[str] = None,
            gc: Optional[Any] = None, id: Optional[str] = None,
            resource: Optional[str] = None,
            editWarp: bool = False, reference: Optional[IPyLeafletMixin] = None,
    ) -> None:
        """
        Specify the large image to be used with the IPyLeaflet Map.  One of (a)
        a tile source, (b) metadata dictionary and tile url, (c) girder client
        and item or file id, or (d) girder client and resource path must be
        specified.

        :param ts: a TileSource.
        :param metadata: a metadata dictionary as returned by a tile source or
            a girder item/{id}/tiles endpoint.
        :param url: a slippy map template url to fetch tiles (e.g.,
            .../item/{id}/tiles/zxy/{z}/{x}/{y}?params=...)
        :param gc: an authenticated girder client.
        :param id: an item id that exists on the girder client.
        :param resource: a girder resource path of an item or file that exists
            on the girder client.
        """
        self._layer = self._map = self._metadata = None
        self.frame_selector: Optional[FrameSelector] = None
        self._frame_histograms: Optional[dict[int, Any]] = None
        self._ts = ts
        self._edit_warp = editWarp
        self._reference = reference
        self._reference_layer = None
        if self._edit_warp:
            self.warp_points: dict[str, list[Optional[list[int]]]] = dict(src=[], dst=[])
            self._warp_widgets: dict = dict()
            self._warp_markers: dict = {'src': [], 'dst': []}
            self._dragging_marker_id: Optional[str] = None
        if (not url or not metadata) and gc and (id or resource):
            fileId = None
            if id is None:
                entry = gc.get('resource/lookup', parameters={'path': resource})
                if entry:
                    if entry.get('_modelType') == 'file':
                        fileId = entry['_id']
                    id = entry['itemId'] if entry.get('_modelType') == 'file' else entry['_id']
            if id:
                try:
                    metadata = gc.get(f'item/{id}/tiles')
                except Exception:
                    pass
                if metadata:
                    url = gc.urlBase + f'item/{id}/tiles' + '/zxy/{z}/{x}/{y}'
                    if metadata.get('geospatial'):
                        suffix = '?projection=EPSG:3857&encoding=PNG'
                        metadata = gc.get(f'item/{id}/tiles' + suffix)
                        if (cast(dict, metadata).get('geospatial') and
                                cast(dict, metadata).get('projection')):
                            url += suffix
                    self._id = id
                else:
                    self._ts = self._get_temp_source(gc, cast(str, fileId or id))
        if url and metadata:
            self._metadata = metadata
            self._url = url
            self._layer = self.make_layer(metadata, url)
            self._map = self.make_map(metadata)

    if ipyleafletPresent:
        def _ipython_display_(self) -> Any:
            from IPython.display import display

            if self._map:
                return display(self._map)
            if self._ts:
                t = self._ts.as_leaflet_layer()
                return display(self._ts._map.make_map(
                    self._ts.metadata,  # type: ignore[attr-defined]
                    t,
                    self._ts.getCenter(srs='EPSG:4326')))  # type: ignore[attr-defined]

    def _get_temp_source(self, gc: Any, id: str) -> IPyLeafletMixin:
        """
        If the server isn't large_image enabled, download the file to view it.
        """
        import tempfile

        import large_image

        try:
            item = gc.get(f'item/{id}')
        except Exception:
            item = None
        if not item:
            file = gc.get(f'file/{id}')
        else:
            file = gc.get(f'item/{id}/files', parameters={'limit': 1})[0]
        self._tempfile = tempfile.NamedTemporaryFile(suffix='.' + file['name'].split('.', 1)[-1])
        gc.downloadFile(file['_id'], self._tempfile)
        return large_image.open(self._tempfile.name)

    def make_layer(self, metadata: dict, url: str, **kwargs) -> Any:
        """
        Create an ipyleaflet tile layer given large_image metadata and a tile
        url.
        """
        from ipyleaflet import TileLayer

        self._geospatial = metadata.get('geospatial') and metadata.get('projection')
        if 'bounds' not in kwargs and not self._geospatial:
            kwargs = kwargs.copy()
            kwargs['bounds'] = [[0, 0], [metadata['sizeY'], metadata['sizeX']]]
        layer = TileLayer(
            url=url,
            # attribution='Tiles served with large-image',
            min_zoom=0,
            max_native_zoom=metadata['levels'] - 1,
            max_zoom=20,
            tile_size=metadata['tileWidth'],
            **kwargs,
        )
        self._layer = layer
        if not self._metadata:
            self._metadata = metadata
        return layer

    def make_map(
            self, metadata: dict, layer: Optional[Any] = None,
            center: Optional[tuple[float, float]] = None) -> Any:
        """
        Create an ipyleaflet map given large_image metadata, an optional
        ipyleaflet layer, and the center of the tile source.
        """
        from ipyleaflet import FullScreenControl, Map, basemaps, projections
        from ipywidgets import FloatSlider, VBox

        try:
            default_zoom = metadata['levels'] - metadata['sourceLevels']
        except KeyError:
            default_zoom = 0

        self._geospatial = metadata.get('geospatial') and metadata.get('projection')

        if self._geospatial:
            # TODO: better handle other projections
            crs = projections.EPSG3857
        else:
            crs = dict(
                name='PixelSpace',
                custom=True,
                resolutions=[2 ** (metadata['levels'] - 1 - l) for l in range(20)],

                proj4def='+proj=longlat +axis=esu',
                bounds=[[0, 0], [metadata['sizeX'], metadata['sizeY']]],
                origin=[0, metadata['sizeY']],
            )
        layer = layer or self._layer

        if center is None:
            if 'bounds' in metadata and 'projection' in metadata:
                import pyproj

                bounds = metadata['bounds']
                center = (
                    (bounds['ymax'] + bounds['ymin']) / 2,
                    (bounds['xmax'] + bounds['xmin']) / 2,
                )
                transf = pyproj.Transformer.from_crs(
                    metadata['projection'], 'EPSG:4326', always_xy=True)
                center = tuple(transf.transform(center[1], center[0])[::-1])
            else:
                center = (metadata['sizeY'] / 2, metadata['sizeX'] / 2)

        children: list[Any] = []
        frames = metadata.get('frames')
        if frames is not None and ipyvuePresent and aiohttpPresent:
            self.frame_selector = FrameSelector()
            self.frame_selector.imageMetadata = metadata
            self.frame_selector.updateFrameCallback = self.update_frame
            self.frame_selector.getFrameHistogram = self.get_frame_histogram
            children.append(self.frame_selector)

        m = Map(
            crs=crs,
            basemap=basemaps.OpenStreetMap.Mapnik if self._geospatial else layer,
            center=center,
            zoom=default_zoom,
            max_zoom=metadata['levels'] + 1,
            min_zoom=0,
            scroll_wheel_zoom=True,
            dragging=True,
            attribution_control=False,
        )
        if not self._geospatial:
            m.fit_bounds(bounds=[[0, 0], [metadata['sizeY'], metadata['sizeX']]])
        if self._geospatial:
            m.add_layer(layer)

        if self._reference is not None:
            default_opacity = 0.5
            self._reference_layer = self._reference.as_leaflet_layer()
            if self._reference_layer is not None:
                self._reference_layer.opacity = default_opacity
                m.add_layer(self._reference_layer)

            def update_reference_opacity(event):
                if self._reference_layer is not None:
                    self._reference_layer.opacity = event.get('new', default_opacity)

            reference_slider = FloatSlider(
                description='Reference Opacity',
                value=default_opacity, step=0.1,
                min=0, max=1,
                readout_format='.1f',
                style={'description_width': 'initial'},
            )
            reference_slider.observe(update_reference_opacity, names=['value'])
            children.append(reference_slider)

        self._map = m
        children.append(m)

        if self._edit_warp:
            children.append(self.add_warp_editor())
        else:
            # Only add region indicator if not using warp editor so that
            # the map doesn't have conflicting on_interaction callbacks
            self.add_region_indicator()
        self._map.add(FullScreenControl())
        return VBox(children)

    def warp_editor_validate_source(self):
        if self._ts is None:
            msg = 'Warp editor mode not allowed; source is not defined.'
            raise TileSourceError(msg)

        if not os.path.exists(str(self._ts.largeImagePath)):  # type: ignore[attr-defined]
            msg = 'Warp editor mode not allowed; source file does not exist.'
            raise TileSourceError(msg)

    def convert_coordinate_map_to_warp(self, map_coord):
        y, x = map_coord
        if self._ts is not None:
            y = self._ts.sizeY - y   # type: ignore[attr-defined]
        return [int(x), int(y)]

    def convert_coordinate_warp_to_map(self, warp_coord):
        x, y = warp_coord
        if self._ts is not None:
            y = self._ts.sizeY - y   # type: ignore[attr-defined]
        return [int(y), int(x)]

    def toggle_warp_transform(self, event):
        self.update_warp(event.get('new'))

    def inverse_warp(self, coord):
        _lazyImportSkimageTransform()

        warp_src = np.array(self.warp_points['src'])
        warp_dst = np.array(self.warp_points['dst'])
        n_points = warp_src.shape[0]
        inverse_coord = None
        if n_points == 0:
            return coord
        if n_points == 1:
            if warp_src[0] is not None and warp_dst[0] is not None:
                inverse_coord = [
                    v + warp_src[0][i] - warp_dst[0][i]
                    for i, v in enumerate(coord)
                ]
        elif skimage_transform is not None:
            srcsvd = np.linalg.svd(warp_src - warp_src.mean(axis=0), compute_uv=False)
            dstsvd = np.linalg.svd(warp_dst - warp_dst.mean(axis=0), compute_uv=False)
            useSimilarity = n_points < 3 or min(
                srcsvd[1] / (srcsvd[0] or 1), dstsvd[1] / (dstsvd[0] or 1)) < 1e-3

            if useSimilarity:
                transformer = skimage_transform.SimilarityTransform()
            elif n_points <= 3:
                transformer = skimage_transform.AffineTransform()
            else:
                transformer = skimage_transform.ThinPlateSplineTransform()
            transformer.estimate(warp_dst, warp_src)
            inverse_coord = transformer([coord])[0]
        if inverse_coord is not None:
            return [int(v) for v in inverse_coord]

    def get_warp_schema(self):
        if self._ts is None:
            return None
        schema = dict(sources=[
            dict(
                path=str(self._ts.largeImagePath),  # type: ignore[attr-defined]
                z=0, position=dict(x=0, y=0, warp=self.warp_points),
            ),
        ])
        json_content = json.dumps(schema, indent=4)
        # convert from json to avoid aliases
        yaml_content = yaml.dump(json.loads(json_content))
        return (json_content, yaml_content)

    def copy_warp_schema(self, button):
        from IPython.display import Javascript

        schema_copy_output = self._warp_widgets.get('copy_output')
        if schema_copy_output is not None:
            content = ''
            json_content, yaml_content = self.get_warp_schema()
            desc = button.description
            if 'YAML' in desc:
                content = yaml_content
            elif 'JSON' in desc:
                content = json_content
            content = content.replace('\n', '\\n')
            command = f"navigator.clipboard.writeText(unescape('{content}'))"
            schema_copy_output.clear_output()
            schema_copy_output.append_display_data(Javascript(command))
            button.description = 'Copied!'
            button.icon = 'fa-check'
            time.sleep(2)
            button.description = desc
            button.icon = 'fa-copy'

    def update_warp_schemas(self):
        yaml_schema = self._warp_widgets.get('yaml')
        json_schema = self._warp_widgets.get('json')
        schema_accordion = self._warp_widgets.get('accordion')
        transform_checkbox = self._warp_widgets.get('transform')
        help_text = self._warp_widgets.get('help_text')
        if (
            self._ts is None or
            yaml_schema is None or
            json_schema is None or
            schema_accordion is None or
            transform_checkbox is None or
            help_text is None
        ):
            return
        json_content, yaml_content = self.get_warp_schema()
        yaml_schema.value = f'<pre>{yaml_content}</pre>'
        json_schema.value = f'<pre>{json_content}</pre>'
        schema_accordion.layout.display = 'block'
        transform_checkbox.layout.display = 'block'
        help_text.value = (
            'Reference the schemas below to use this warp with '
            'the MultiFileTileSource (either as YAML or JSON).'
        )
        self.update_warp(transform_checkbox.value)

    def start_drag(self, marker):
        self._dragging_marker_id = marker.title

    def handle_drag(self, coords):
        if self._dragging_marker_id is not None:
            marker_title = self._dragging_marker_id
            group_name = marker_title[:3]
            index = int(marker_title[3:])
            self.warp_points[group_name][index] = self.convert_coordinate_map_to_warp(coords)
            self.update_warp_schemas()

    def end_drag(self):
        self._dragging_marker_id = None

    def create_warp_reference_point_pair(self, coord):
        from ipyleaflet import DivIcon, Marker

        marker_style = (
            'border-radius: 50%; position: relative;'
            'height: 16px; width: 16px; top: -8px; left: -8px;'
            'text-align: center; font-size: 11px;'
        )
        converted = self.convert_coordinate_map_to_warp(coord)
        locations = dict(src=converted, dst=converted)
        transform_checkbox = self._warp_widgets.get('transform')
        transform_enabled = transform_checkbox.value if transform_checkbox is not None else True
        if transform_enabled:
            locations['src'] = self.inverse_warp(locations['src'])
        index = len(self.warp_points['src'])
        self.warp_points['src'].append(locations['src'])
        self.warp_points['dst'].append(locations['dst'])

        for group_name, color in [
            ('src', '#ff6a5e'), ('dst', '#19a7ff'),
        ]:
            html = f'<div style="background-color: {color}; {marker_style}">{index}</div>'
            icon = DivIcon(html=html, icon_size=[0, 0])
            marker = Marker(
                location=self.convert_coordinate_warp_to_map(locations[group_name]),
                draggable=True,
                icon=icon,
                title=f'{group_name} {index}',
                visible=(group_name == 'dst' or not transform_enabled),
            )
            marker.on_dblclick(lambda m=marker, **e: self.remove_warp_reference_point_pair(m))
            marker.on_mousedown(lambda m=marker, **e: self.start_drag(m))
            marker.on_mouseup(lambda **e: self.end_drag())
            self._warp_markers[group_name].append(marker)
            if self._map is not None:
                self._map.add(marker)

    def remove_warp_reference_point_pair(self, marker):
        from ipyleaflet import DivIcon

        index = int(marker.title[3:])
        for group_name in ['src', 'dst']:
            del self.warp_points[group_name][index]
            if self._map is not None:
                self._map.remove(self._warp_markers[group_name][index])
            del self._warp_markers[group_name][index]
            # reset indices of remaining markers
            for i, m in enumerate(self._warp_markers[group_name]):
                m.title = f'{group_name} {i}'
                html = re.sub(r'>\d+<', f'>{i}<', m.icon.html)
                m.icon = DivIcon(html=html, icon_size=[0, 0])
        self.update_warp_schemas()

    def add_warp_editor(self):
        from ipywidgets import HTML, Accordion, Button, Checkbox, Label, Output, VBox

        self.warp_editor_validate_source()
        help_text = Label('To begin editing a warp, click on the image to place reference points.')
        transform_checkbox = Checkbox(description='Show Transformed', value=True)
        transform_checkbox.layout.display = 'none'
        transform_checkbox.observe(self.toggle_warp_transform, names=['value'])
        yaml_schema = HTML('yaml')
        json_schema = HTML('json')
        copy_yaml_button = Button(description='Copy YAML', icon='fa-copy')
        copy_json_button = Button(description='Copy JSON', icon='fa-copy')
        copy_yaml_button.on_click(self.copy_warp_schema)
        copy_json_button.on_click(self.copy_warp_schema)
        yaml_box = VBox(children=[copy_yaml_button, yaml_schema])
        json_box = VBox(children=[copy_json_button, json_schema])
        schema_accordion = Accordion(children=[yaml_box, json_box], titles=('YAML', 'JSON'))
        schema_accordion.layout.display = 'none'
        schema_copy_output = Output()
        schema_copy_output.layout.display = 'none'
        self._warp_widgets = dict(
            help_text=help_text,
            transform=transform_checkbox,
            yaml=yaml_schema,
            json=json_schema,
            accordion=schema_accordion,
            copy_output=schema_copy_output,
        )

        def handle_interaction(**kwargs):
            event_type = kwargs.get('type')
            coords = [round(v) for v in kwargs.get('coordinates', [])]
            if event_type == 'click':
                self.create_warp_reference_point_pair(coords)
                self.update_warp_schemas()
                help_text.value = (
                    'After placing reference points, you can drag them to define the warp. '
                    'You may also double-click any point to remove the point pair.'
                )
            elif event_type == 'mousemove':
                self.handle_drag(coords)

        if self._map is not None:
            self._map.on_interaction(handle_interaction)
        return VBox([transform_checkbox, help_text, schema_accordion, schema_copy_output])

    def add_region_indicator(self):
        from ipyleaflet import GeomanDrawControl, Popup
        from ipywidgets import HTML

        metadata = self._metadata
        if self._map is None or metadata is None:
            return

        self.info_label = HTML()
        popup = Popup(child=self.info_label)
        popup.close_popup()
        draw_control = GeomanDrawControl(
            rectangle=dict(shapeOptions=dict(color='#19a7ff')),
            # enable drawing other shapes by specifying styling
            polygon=dict(),
            circle=dict(),
            polyline=dict(),
            circlemarker=dict(),
            rotate=False,
            cut=False,
            edit=False,
        )

        transformer = None
        if metadata.get('geospatial') and metadata.get('projection'):
            import pyproj

            transformer = pyproj.Transformer.from_crs(
                'EPSG:4326',
                metadata['projection'],
                always_xy=True,
            )

        def handle_interaction(**kwargs):
            coords = kwargs.get('coordinates')
            info = []
            if self._map is None or metadata is None or coords is None:
                return
            x, y = [coords[1], coords[0]]
            interaction_type = kwargs.get('type')
            if interaction_type == 'click':
                for rectangle in draw_control.data:
                    rect_coords = rectangle.get('geometry', {}).get('coordinates', [[]])[0]
                    xmin, xmax = rect_coords[0][0], rect_coords[2][0]
                    ymin, ymax = rect_coords[0][1], rect_coords[1][1]
                    width, height = metadata['sizeX'], metadata['sizeY']
                    if (not (x >= xmin and x <= xmax and y >= ymin and y <= ymax)):
                        continue
                    if transformer is not None:
                        roi = f'[{xmin:.8g}, {ymin:.8g}, {(xmax - xmin):.8g}, {(ymax - ymin):.8g}]'
                        info.append(f'Lon Range: [{xmin:.8g}, {xmax:.8g}]')
                        info.append(f'Lat Range: [{ymin:.8g}, {ymax:.8g}]')
                        info.append(f'Lon/Lat ROI: {roi}')
                        x0, y0 = transformer.transform(xmin, ymin)
                        x1, y1 = transformer.transform(xmax, ymax)
                        bounds = metadata['bounds']
                        x0, x1 = (
                            round((v - bounds['xmin']) /
                                  (bounds['xmax'] - bounds['xmin']) *
                                  width) for v in [x0, x1]
                        )
                        y0, y1 = (
                            round((v - bounds['ymax']) /
                                  (bounds['ymin'] - bounds['ymax']) *
                                  height) for v in [y1, y0]
                        )
                        info.append(f'X/Y ROI: [{x0}, {y0}, {x1 - x0}, {y1 - y0}]')
                    else:
                        xmin, xmax = round(xmin), round(xmax)
                        ymin, ymax = round(height - ymax), round(height - ymin)
                        roi = f'[{xmin:.8g}, {ymin:.8g}, {(xmax - xmin):.8g}, {(ymax - ymin):.8g}]'
                        info.append(f'X Range: [{xmin:.8g}, {xmax:.8g}]')
                        info.append(f'Y Range: [{ymin:.8g}, {ymax:.8g}]')
                        info.append(f'X/Y ROI: {roi}')
                    self.info_label.value = ''.join(f'<div>{i}</div>' for i in info)
                    popup.open_popup((rect_coords[1][1], (xmax - xmin) / 2 + xmin))
                    if popup not in self._map.layers:
                        self._map.add(popup)

        def handle_draw(target, action, geo_json):
            if action == 'deleted':
                popup.close_popup()

        draw_control.on_draw(handle_draw)
        self._map.on_interaction(handle_interaction)
        self._map.add(draw_control)

    @property
    def layer(self) -> Any:
        return self._layer

    @property
    def map(self) -> Any:
        return self._map

    @property
    def metadata(self) -> JSONDict:
        return JSONDict(self._metadata)

    @property
    def id(self) -> Optional[str]:
        return getattr(self, '_id', None)

    def to_map(self, coordinate: Union[list[float], tuple[float, float]]) -> tuple[float, float]:
        """
        Convert a coordinate from the image or projected image space to the map
        space.

        :param coordinate: a two-tuple that is x, y in pixel space or x, y in
            image projection space.
        :returns: a two-tuple that is in the map space coordinates.
        """
        x, y = coordinate[:2]
        if not self._metadata:
            return y, x
        if self._geospatial:
            import pyproj

            transf = pyproj.Transformer.from_crs(
                self._metadata['projection'], 'EPSG:4326', always_xy=True)
            return tuple(transf.transform(x, y)[::-1])
        return self._metadata['sizeY'] - y, x

    def from_map(self, coordinate: Union[list[float], tuple[float, float]]) -> tuple[float, float]:
        """
        :param coordinate: a two-tuple that is in the map space coordinates.
        :returns: a two-tuple that is x, y in pixel space or x, y in image
            projection space.
        """
        y, x = coordinate[:2]
        if not self._metadata:
            return x, y
        if self._geospatial:
            import pyproj

            transf = pyproj.Transformer.from_crs(
                'EPSG:4326', self._metadata['projection'], always_xy=True)
            return transf.transform(x, y)
        return x, self._metadata['sizeY'] - y

    def update_warp(self, show_warp):
        for marker in self._warp_markers['src']:
            marker.visible = not show_warp
        current_frame = self.frame_selector.currentFrame if self.frame_selector is not None else 0
        if show_warp and len(self.warp_points['src']):
            self.update_layer_query(frame=current_frame, style=dict(warp=self.warp_points))
        else:
            self.update_layer_query(frame=current_frame, style=dict())

    def update_frame(self, frame, style, **kwargs):
        if self._edit_warp:
            transform_checkbox = self._warp_widgets.get('transform')
            if (
                transform_checkbox is not None and
                transform_checkbox.value and
                self.warp_points is not None and
                len(self.warp_points['src'])
            ):
                style['warp'] = self.warp_points
        self.update_layer_query(frame=frame, style=style)

    def update_layer_query(self, frame, style, **kwargs):
        if self._layer:
            parsed_url = urlparse(self._layer.url)
            query = parsed_url.query
            query = {k: v[0] for k, v in parse_qs(query).items()}
            query.update(dict(
                frame=frame,
                style=json.dumps(style),
            ))
            query_string = urlencode(query, quote_via=quote, safe='{}')
            self._layer.url = urlunparse((
                parsed_url.scheme, parsed_url.netloc,
                parsed_url.path, parsed_url.params,
                query_string, parsed_url.fragment,
            ))
            self._layer.redraw()

    def get_frame_histogram(self, query):
        import aiohttp

        if self._layer is not None:
            if self._frame_histograms is None:
                self._frame_histograms = {}

            frame = query.get('frame')
            parsed_url = urlparse(self._layer.url)
            query_string = urlencode(query)
            scheme = parsed_url.scheme or 'http'
            netloc = parsed_url.netloc
            if not netloc and self._ts is not None:
                netloc = f'{self._ts.JUPYTER_HOST}:{self._ts._jupyter_server_manager.port}'
            histogram_url = urlunparse((
                scheme, netloc,
                '/histogram', parsed_url.params,
                query_string, parsed_url.fragment,
            ))

            async def fetch(url):
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=900),
                ) as session:
                    async with session.get(url) as response:
                        self._frame_histograms[frame] = await response.json()  # type: ignore
                        # rewrite whole object for watcher
                        if self.frame_selector is not None and self._frame_histograms is not None:
                            self.frame_selector.frameHistograms = (
                                self._frame_histograms.copy()  # type: ignore
                            )

            asyncio.ensure_future(fetch(histogram_url))


# used for encoding histogram data
class NumpyEncoder(json.JSONEncoder):
    """Special json encoder for numpy types from https://stackoverflow.com/a/49677241"""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


multi_source = None


def _lazyImportMultiSource():
    """
    Import the large_image_source_multi module. This is only needed when editWarp is used.
    """
    global multi_source

    if multi_source is None:
        try:
            import large_image_source_multi as multi_source
        except ImportError:
            msg = 'large_image_source_multi module not found.'
            raise TileSourceError(msg)


class RequestManager:
    def __init__(self, tile_source: IPyLeafletMixin) -> None:
        self._tile_source_ = weakref.ref(tile_source)
        self._ports = ()

    @property
    def tile_source(self) -> IPyLeafletMixin:
        return cast(IPyLeafletMixin, self._tile_source_())

    @tile_source.setter
    def tile_source(self, source: IPyLeafletMixin) -> None:
        self._tile_source_ = weakref.ref(source)

    @property
    def ports(self) -> tuple[int, ...]:
        return self._ports

    @property
    def port(self) -> int:
        return self.ports[0]

    def get_warp_source(self, warp):
        _lazyImportMultiSource()
        if multi_source is not None and self.tile_source is not None:
            return multi_source.open(dict(
                sources=[
                    dict(
                        path=str(self.tile_source.largeImagePath),
                        position=dict(
                            x=0, y=0, warp=warp,
                        ),
                    ),
                ],
                width=self.tile_source.sizeX,
                height=self.tile_source.sizeY,
            ), noCache=False)


def launch_tile_server(tile_source: IPyLeafletMixin, port: int = 0) -> Any:
    import tornado.httpserver
    import tornado.netutil
    import tornado.web

    manager = RequestManager(tile_source)
    # NOTE: set `ports` manually after launching server

    class TileSourceMetadataHandler(tornado.web.RequestHandler):
        """REST endpoint to get image metadata."""

        def get(self) -> None:
            self.write(json.dumps(manager.tile_source.metadata))  # type: ignore[attr-defined]
            self.set_header('Content-Type', 'application/json')

    class TileSourceHistogramHandler(tornado.web.RequestHandler):
        """REST endpoint to get image metadata."""

        async def get(self) -> None:
            kwargs = {k: ast.literal_eval(self.get_argument(k)) for k in self.request.arguments}

            def fetch():
                if not hasattr(manager, '_histogram_semaphore'):
                    manager._histogram_semaphore = threading.Semaphore(  # type: ignore
                        min(6, large_image.config.cpu_count()),
                    )
                with manager._histogram_semaphore:  # type: ignore[attr-defined]
                    histogram = manager.tile_source._unstyled.histogram(  # type: ignore
                        **kwargs,
                    ).get('histogram', [{}])
                self.write(json.dumps(histogram, cls=NumpyEncoder))
                self.set_header('Content-Type', 'application/json')

            await tornado.ioloop.IOLoop.current().run_in_executor(None, fetch)

    class TileSourceTileHandler(tornado.web.RequestHandler):
        """REST endpoint to serve tiles from image in slippy maps standard."""

        def get(self) -> None:
            x = int(self.get_argument('x'))
            y = int(self.get_argument('y'))
            z = int(self.get_argument('z'))
            frame = int(self.get_argument('frame', default='0'))
            style = self.get_argument('style', default=None)
            warp = None
            encoding = self.get_argument('encoding', 'PNG')
            if style:
                style = json.loads(style)
                warp = style.get('warp')
                if warp is None:
                    manager.tile_source.style = style  # type: ignore[attr-defined]
            try:
                source = manager.tile_source
                if warp is not None:
                    source = manager.get_warp_source(warp)
                tile_binary = source.getTile(  # type: ignore[attr-defined]
                    x, y, z, encoding=encoding, frame=frame)
            except TileSourceXYZRangeError as e:
                self.clear()
                self.set_status(404)
                self.finish(f'<html><body>{e}</body></html>')
            else:
                self.write(tile_binary)
                self.set_header('Content-Type', 'image/png')

    app = tornado.web.Application([
        (r'/metadata', TileSourceMetadataHandler),
        (r'/histogram', TileSourceHistogramHandler),
        (r'/tile', TileSourceTileHandler),
    ])
    sockets = tornado.netutil.bind_sockets(port, '')
    server = tornado.httpserver.HTTPServer(app)
    server.add_sockets(sockets)

    manager._ports = tuple(s.getsockname()[1] for s in sockets)
    return manager
