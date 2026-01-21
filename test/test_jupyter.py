import asyncio
import json
import os
from urllib.parse import parse_qs, urlparse

import aiohttp
import pytest
import yaml

import large_image

try:
    import ipyleaflet  # noqa: F401
    import IPython  # noqa: F401
    import tornado  # noqa: F401
except ImportError:  # pragma: no cover
    pytest.skip(reason='Requires ipyleaflet, tornado, IPython', allow_module_level=True)


def testJupyterIpyleafletGeospatial():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    source = large_image.open(imagePath, projection='EPSG:3857', noCache=True)
    assert source.geospatial
    assert source.projection
    source._ipython_display_()  # smoke test
    # Run twice to make sure launched only once
    port = source._jupyter_server_manager.port
    source._ipython_display_()  # smoke test
    assert source._jupyter_server_manager.port == port


@pytest.mark.asyncio
async def testJupyterIpyleafletMultiFrame():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'multi_channels.yml')
    source = large_image.open(imagePath, projection='EPSG:3857', noCache=True)
    assert source.frames

    # get display in same method as _ipython_display_
    display = source._map.make_map(
        source.metadata, source.as_leaflet_layer(), source.getCenter(srs='EPSG:4326'),
    )
    # ensure first child is frame selector widget
    assert display.children[0].__class__.__name__ == 'FrameSelector'
    frame_selector = display.children[0]

    # test update_frame
    expected_query_keys = {'x', 'y', 'z', 'encoding', 'repr'}
    parsed_url = urlparse(source._map._layer.url)
    query = parse_qs(parsed_url.query)
    assert set(query.keys()) == expected_query_keys
    source._map.update_frame(frame=2, style=dict(band=2))
    expected_query_keys.add('frame')
    expected_query_keys.add('style')
    parsed_url = urlparse(source._map._layer.url)
    query = parse_qs(parsed_url.query)
    assert set(query.keys()) == expected_query_keys
    assert query.get('frame') == ['2']
    assert query.get('style') == ['{"band": 2}']

    # test get_frame_histogram
    expected_histogram_keys = {
        'min', 'max', 'mean',
        'stdev', 'range', 'hist',
        'bins', 'bin_edges', 'density', 'samples',
    }
    assert frame_selector.frameHistograms == {}
    source._map.get_frame_histogram(dict(frame=2))
    await asyncio.sleep(0.5)
    histograms = frame_selector.frameHistograms
    assert set(histograms.keys()) == {2}
    assert len(histograms.get(2)) == 1
    assert set(histograms.get(2)[0].keys()) == expected_histogram_keys


@pytest.mark.asyncio
async def testJupyterIpyleaflet():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'test_orient0.tif')
    source = large_image.open(imagePath, noCache=True)
    source._ipython_display_()  # smoke test
    port = source._jupyter_server_manager.port

    async def fetch(url):
        async with aiohttp.ClientSession() as session, session.get(url) as response:
            return response

    r = await fetch(f'http://localhost:{port}/tile?z=0&x=0&y=0&encoding=png')
    r.raise_for_status()
    assert r.content
    r = await fetch(f'http://localhost:{port}/metadata')
    r.raise_for_status()
    assert r.content


def testJupyterIpyleafletMapRegion():
    from ipyleaflet import GeomanDrawControl

    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'test_orient0.tif')
    source = large_image.open(imagePath, noCache=True)
    display = source._map.make_map(
        source.metadata, source.as_leaflet_layer(), source.getCenter(srs='EPSG:4326'),
    )
    assert len(display.children)
    m = display.children[0]
    assert len(m.controls)

    height = source.metadata['sizeY']
    xmin, xmax, ymin, ymax = 10, 90, 30, 100
    x, y = 50, 100
    expected = [f'X Range: [{xmin}, {xmax}]']
    expected.append(f'Y Range: [{ymin}, {ymax}]')
    expected.append(f'X/Y ROI: [{xmin}, {ymin}, {xmax - xmin}, {ymax - ymin}]')

    rectangle = [[
        [xmin, height - ymax],
        [xmin, height - ymin],
        [xmax, height - ymax],
        [xmax, height - ymin],
    ]]
    for control in m.controls:
        if isinstance(control, GeomanDrawControl):
            control.data = [
                dict(geometry=dict(coordinates=rectangle)),
            ]
    for callback in m._interaction_callbacks.callbacks:
        callback(type='click', coordinates=[y, x])
    assert source._map.info_label.value == ''.join([f'<div>{e}</div>' for e in expected])


def testJupyterIpyleafletMapGeospatialRegion():
    from ipyleaflet import GeomanDrawControl

    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    source = large_image.open(imagePath, projection='EPSG:3857', noCache=True)
    display = source._map.make_map(
        source.metadata, source.as_leaflet_layer(), source.getCenter(srs='EPSG:4326'),
    )
    assert len(display.children)
    m = display.children[0]
    assert len(m.controls)

    lonmin, lonmax, latmin, latmax = -118, -116, 32.5, 34
    lon, lat = -117, 33
    roi = [11562, 7156, 52322, 46301]
    expected = [f'Lon Range: [{lonmin}, {lonmax}]']
    expected.append(f'Lat Range: [{latmin}, {latmax}]')
    expected.append(f'Lon/Lat ROI: [{lonmin}, {latmin}, {lonmax - lonmin}, {latmax - latmin}]')
    expected.append(f'X/Y ROI: {roi}')

    rectangle = [[
        [lonmin, latmin],
        [lonmin, latmax],
        [lonmax, latmax],
        [lonmax, latmin],
    ]]
    for control in m.controls:
        if isinstance(control, GeomanDrawControl):
            control.data = [
                dict(geometry=dict(coordinates=rectangle)),
            ]
    for callback in m._interaction_callbacks.callbacks:
        callback(type='click', coordinates=[lat, lon])
    assert source._map.info_label.value == ''.join([f'<div>{e}</div>' for e in expected])


def testJupyterReferenceLayer():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath1 = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    imagePath2 = os.path.join(testDir, 'test_files', 'rgba_geotiff.tiff')
    source1 = large_image.open(imagePath1, projection='EPSG:3857', noCache=True)
    source2 = large_image.open(imagePath2, projection='EPSG:3857', noCache=True, reference=source1)
    display = source2._map.make_map(
        source2.metadata, source2.as_leaflet_layer(), source2.getCenter(srs='EPSG:4326'),
    )
    assert len(display.children) == 2
    [slider, leafletMap] = display.children
    assert slider.description == 'Reference Opacity'
    for path in [imagePath1, imagePath2]:
        assert any(path in layer.url for layer in leafletMap.layers)


def initEditWarp():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    source = large_image.open(imagePath, projection='EPSG:3857', noCache=True, editWarp=True)
    display = source._map.make_map(
        source.metadata, source.as_leaflet_layer(), source.getCenter(srs='EPSG:4326'),
    )
    return source._map, display


def testJupyterEditWarp():
    _, display = initEditWarp()
    assert len(display.children) == 2
    vbox = display.children[1]
    assert len(vbox.children) == 4
    assert vbox.children[0].description == 'Show Transformed'
    assert vbox.children[0].layout.display == 'none'
    assert vbox.children[1].value == (
        'To begin editing a warp, click on the image to place reference points.'
    )
    assert vbox.children[2].titles == ('YAML', 'JSON')
    assert vbox.children[3].layout.display == 'none'


def testJupyterEditWarpConvertCoords():
    sourceMap, _ = initEditWarp()
    assert sourceMap.convert_coordinate_map_to_warp([10, 12]) == [12, 65526]
    assert sourceMap.convert_coordinate_warp_to_map([12, 65526]) == [10, 12]


def testJupyterEditWarpCreateAndDeletePointPairs():
    sourceMap, _ = initEditWarp()
    sourceMap.create_warp_reference_point_pair([10, 10])
    assert len(sourceMap._warp_markers['src']) == 1
    assert len(sourceMap._warp_markers['dst']) == 1
    marker = sourceMap._warp_markers['src'][0]
    assert marker.location == [10, 10]
    sourceMap.remove_warp_reference_point_pair(marker)
    assert len(sourceMap._warp_markers['src']) == 0
    assert len(sourceMap._warp_markers['dst']) == 0


def testJupyterEditWarpSchemas():
    sourceMap, display = initEditWarp()
    warp = dict(
        src=[[10, 10]],
        dst=[[15, 15]],
    )
    expected = dict(sources=[
        dict(
            path=str(sourceMap._ts.largeImagePath),
            z=0, position=dict(x=0, y=0, warp=warp),
        ),
    ])
    sourceMap.warp_points = warp
    sourceMap.update_warp_schemas()
    json_schema = sourceMap._warp_widgets.get('json')
    assert json_schema.value == f'<pre>{json.dumps(expected, indent=4)}</pre>'
    yaml_schema = sourceMap._warp_widgets.get('yaml')
    assert yaml_schema.value == f'<pre>{yaml.dump(expected)}</pre>'

    assert len(display.children) == 2
    vbox = display.children[1]
    assert len(vbox.children) == 4
    copy_output = vbox.children[3]
    accordion = vbox.children[2]
    yaml_section = accordion.children[0]
    copy_yaml_button = yaml_section.children[0]
    sourceMap.copy_warp_schema(copy_yaml_button)
    assert len(copy_output.outputs) == 1
    output = copy_output.outputs[0]
    assert output['data']['application/javascript'] == (
        "navigator.clipboard.writeText(unescape('%s'))"
        % yaml.dump(expected).replace('\n', '\\n')
    )


def testJupyterEditWarpInverseWarp():
    sourceMap, _ = initEditWarp()
    # inverse from single ref point
    sourceMap.warp_points = dict(
        src=[[10, 10]],
        dst=[[15, 15]],
    )
    assert sourceMap.inverse_warp([5, 5]) == [0, 0]
    # inverse from two ref points
    sourceMap.warp_points = dict(
        src=[[10, 10], [5, 5]],
        dst=[[15, 15], [3, 4]],
    )
    assert sourceMap.inverse_warp([2, 4]) == [4, 4]
    # inverse from three ref points
    sourceMap.warp_points = dict(
        src=[[10, 10], [5, 5], [2, 4]],
        dst=[[15, 15], [3, 4], [3, 6]],
    )
    assert sourceMap.inverse_warp([6, 9]) == [2, 5]
    # inverse from four ref points
    sourceMap.warp_points = dict(
        src=[[10, 10], [5, 5], [2, 4], [6, 9]],
        dst=[[15, 15], [3, 4], [3, 6], [3, 5]],
    )
    assert sourceMap.inverse_warp([8, 8]) == [7, 6]
