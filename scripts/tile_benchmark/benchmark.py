#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#############################################################################

import argparse
import math
import six
import sys


import numpy as np
import requests


class MetaData:
    def __init__(self):
        self.url = None
        self.num_levels = None
        self.num_x_tiles = None
        self.num_y_tiles = None
        self.slide_atlas_arr = None


def main(file_name):
    """Read in request data from source.txt, request tiles from each server and
    visualize response times
    """
    print(file_name)
    run_params = {}
    # read in servers to request
    with open(file_name, 'r') as params:
        for line in params:
            if '#' not in line:
                print(line)
                args = line.split()
                # second item in source/config file is the server name
                run_params[args[1]] = args
    # get elapsed time for data requests
    for server_name in six.viewkeys(run_params):
        host = run_params[server_name][0]
        # atlas and
        if host == 'atlas':
            print('Getting images from atlas')
            elapsed_time = get_data(
                host,
                int(run_params[server_name][2]),
                int(run_params[server_name][3]))
        elif host == 'iip':
            print('Getting images from iip')
            elapsed_time = get_data(
                host,
                int(run_params[server_name][2]),
                int(run_params[server_name][3]))
        elif host == 'girder':
            print('Getting images from girder')
            elapsed_time = get_data(
                host,
                int(run_params[server_name][2]),
                int(run_params[server_name][3]),
                run_params[server_name][4],
                run_params[server_name][5]
            )

        run_params[server_name].append(elapsed_time)

    save(run_params)


def get_data(host, requested_levels, requested_num_tiles, url=None,
             image_id=None):
    """Get request information for the and request tiles"""
    num_levels = -1
    data = MetaData()
    # get data about server, host url and params
    if host == 'atlas':
        data = atlas_init()
    elif host == 'iip':
        data = iip_init()
    else:
        data = girder_init(url, image_id)

    num_levels = data.num_levels
    # if successful begin to grab tiles from each level
    if num_levels != -1:
        if requested_levels > num_levels:
            requested_levels = num_levels
        # get elapsed time info numpy array include
        elapsed_time_arr, count = \
            iterate_over_tiles(
                host,
                data,
                requested_levels,
                requested_num_tiles)

        return elapsed_time_arr


def _get_coor(requested_levels):
    for z in six.moves.range(requested_levels):
        print('started level %d' % (z))
        for x in six.moves.range(2 ** z):
            for y in six.moves.range(2 ** z):
                yield z, x, y


def iterate_over_tiles(host, data, requested_levels, requested_num_tiles):
    """
    Iterate from level 0 to requested_levels asking for tiles
    """
    total_tiles = sum(2 ** (z * 2) for z in six.moves.range(requested_levels))

    count = 0
    elapsed_time_arr = np.zeros([total_tiles], dtype=float)
    # collect from all levels
    for z, x, y in _get_coor(requested_levels):
        if host == 'atlas':
            request_time = atlas_request(data, z, x, y)
        elif host == 'iip':
            request_time = iip_request(data, z, x, y)
        else:
            request_time = girder_request(data, z, x, y)
        if request_time != -1:
            elapsed_time_arr[count] = request_time * 1000
            count += 1
            if count == requested_num_tiles:
                break
    if count != requested_num_tiles:
        print('Could not query %d tiles with only %d levels, \
            for host %s, could only query %d tiles') % (
            requested_num_tiles, requested_levels, host, count)
    elapsed_time_arr.resize((count))
    return elapsed_time_arr, count


def iip_init():
    data = MetaData()

    data.url = 'http://digitalslidearchive.emory.edu/fcgi-bin/iipsrv' \
               'Openslide.fcgi?DeepZoom=/GLOBAL_SCRATCH/PREUSS_LAB/BATCH1/' \
               '19775.svs_files/%d/%d_%d.jpg'
    data.num_levels = 10
    return data


def atlas_init():
    data = MetaData()
    num_level = 9
    image_id = '500c3e674834a3119800000c'
    database_id = '5074589002e31023d4292d83'
    url = 'https://slide-atlas.org/tile?img=%(img_id)s&db=%(db_id)s' % {
        'img_id': image_id, 'db_id': database_id}
    data.url = url + '&name=%s.jpg'
    data.num_levels = num_level
    pos_list = []

    base = np.arr = np.empty((2, 2), dtype=str)
    base[0, 0] = 'q'
    base[0, 1] = 'r'
    base[1, 0] = 't'
    base[1, 1] = 's'
    for level in six.moves.range(num_level):
        level_arr = np.empty(
            ((2 ** level), (2 ** level)),
            dtype='|S%s' % (level + 1))
        pos_list.append(level_arr)
    # init first tile / the thumbnail to be just t
    pos_list[0][0, 0] = 't'
    for level in six.moves.range(num_level - 1):
        current_arr = pos_list[level]
        next_arr = pos_list[(level + 1)]

        for x in six.moves.range(2 ** level):
            for y in six.moves.range(2 ** level):
                # calculate top corner of next arr
                x_next = x * 2
                y_next = y * 2
                for ix in six.moves.range(2):
                    for iy in six.moves.range(2):
                        next_arr[y_next + iy, x_next + ix] = \
                            np.core.defchararray.add(
                                current_arr[y, x],
                                base[iy, ix]
                            )
    data.slide_atlas_arr = pos_list
    return data


def girder_init(host, image_id):
    image_summary_url = '%sapi/v1/item/%s/tiles' % (host, image_id)
    image_summary_req = requests.get(image_summary_url)

    data = MetaData()
    if image_summary_req.status_code == requests.codes.ok:
        try:
            img_data = image_summary_req.json()

            data.num_x_tiles = math.ceil(img_data['sizeX'] /
                                         img_data['tileWidth'])
            data.num_y_tiles = math.ceil(img_data['sizeY'] /
                                         img_data['tileHeight'])
            url = '%(host_name)sapi/v1/item/%(img_num)s/tiles/zxy/' \
                  % {'host_name': host, 'img_num': image_id}

            data.url = url + '%d/%d/%d'
            data.num_levels = img_data['levels']
        except ValueError:
            print(' Error parsing image summary data from the following '
                  'request \n %s' % (image_summary_url))
            sys.exit()
    else:
        print('Could not receive meta data using the following request\n %s' %
              image_summary_url)
        sys.exit()

    return data


def girder_request(data, z, x, y):
    # calc range of actual tiles
    x_range = int(math.ceil(data.num_x_tiles /
                            2 ** ((data.num_levels - 1) - z)))
    y_range = int(math.ceil(data.num_y_tiles /
                            2 ** ((data.num_levels - 1) - z)))

    if x >= x_range or y >= y_range:
        return -1
    tile_req = requests.get(data.url % (z, x, y))
    elapsed_time = tile_req.elapsed.total_seconds()

    if tile_req.status_code == requests.codes.ok:
        # i = Image.open(StringIO(tile_req.content))
        # i.show()
        return elapsed_time

    elif tile_req.status_code == 404:
        print('404 error to get tile from layer %d x %d y %d error code %d' % (
              z, x, y, tile_req.status_code))
        return -1

    elif tile_req.status_code != 404:
        print('error to get tile from layer %d x %d y %d error code %d' % (
              z, x, y, tile_req.status_code))
        return -1


def atlas_request(data, z, x, y):
    tile_req = requests.get(data.url % (data.slide_atlas_arr[z][y, x]))
    elapsed_time = tile_req.elapsed.total_seconds()

    if tile_req.status_code == requests.codes.ok:
        # print elapsed_time
        # i = Image.open(StringIO(tile_req.content))
        # i.show()
        return elapsed_time
    elif tile_req.status_code == 404:
        return -1

    elif tile_req.status_code != 404:
        print('error to get tile from layer %d x %d y %d error code %d' % (
              z, x, y, tile_req.status_code))
        return -1


def iip_request(data, z, x, y):
    # levels are offset by 8
    tile_req = requests.get(data.url % (z + 8, x, y))
    elapsed_time = tile_req.elapsed.total_seconds()

    if tile_req.status_code == requests.codes.ok:
        # i = Image.open(StringIO(tile_req.content))
        # i.show()
        return elapsed_time

    else:
        tile_req.status_code == 404

        return -1


def save(data):
    """
    Save file as server_type-server_name
    """
    for server_name in six.viewkeys(data):
        elapsed_time = data[server_name][-1]
        host = data[server_name][0]
        data_file_name = '%s-%s_elapsed_time' % (host, server_name)
        np.savetxt(data_file_name, elapsed_time)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Benchmark servers in'
                                                 ' config file'
                                     )
    parser.add_argument('config', nargs='?',
                        default='source.txt', help='path to source/config file')
    main(parser.parse_args().config)
