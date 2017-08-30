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
import numpy as np
import matplotlib.pyplot as plt
import six
import matplotlib.patches as mpatches

import mpl_toolkits.mplot3d.axes3d  # noqa


def main(file_list, units):
    print(file_list, units)
    data = {}
    for file in file_list:
        elapsed_time = np.loadtxt(file)
        data[file] = elapsed_time
        if units == 's':
            data[file] = data[file] * 1000
    plot_data(data)


def plot_data(data):
    """Three graphs are generated, a histogram with overlapping bars a histogram
    with non overlapping bars and a 3d histogram
    """
    colors = ['r', 'g', 'b']
    server_color = {}
    frequency_dict = {}
    overall_max = 1000
    # need to calculate the max time among all servers to serve as the last bin
    for server_name in six.viewkeys(data):
        server_color[server_name] = colors.pop()
        elapsed_time = data[server_name]
        overall_max = max(overall_max, np.amax(elapsed_time))
    interval = np.arange(0, 1000, 50).tolist()
    interval.append(overall_max)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    for server_name in six.viewkeys(data):
        elapsed_time = data[server_name]
        max_val = np.amax(elapsed_time)
        mean_val = np.mean(elapsed_time)
        print('server %s  data has a mean value of %f milliseconds and a max '
              'value of %f milliseconds' % (server_name, mean_val, max_val))
        num, bins, patch = ax.hist(
            elapsed_time,
            interval,
            label=server_name,
            histtype='bar', color=server_color[server_name], alpha=.5)
        frequency_dict[server_name] = num
        ax.set_xticks(bins)

    ax.grid(which='both')
    ax.legend(loc='upper center', shadow=True)
    plt.xlabel('Time to receive tile in seconds')
    plt.ylabel('Frequency')
    plt.title('Elapsed time to receive tiles ')

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    count = 0
    num_bins = len(interval)
    num_servers = len(data)
    bar_width = 1.0 / num_servers
    left_bar_pos = np.arange(1.5, (num_bins) * 1.5, 1.5)
    ax.set_xticks(left_bar_pos)

    interval_label = ['%d-%d' % (interval[i], interval[i + 1])
                      for i in six.moves.range(len(interval) - 1)]
    ax.set_xticklabels(interval_label)
    for server_name in six.viewkeys(data):
        plt.bar((left_bar_pos - 1.5 * bar_width) + count * bar_width,
                frequency_dict[server_name],
                bar_width, label=server_name,
                color=server_color[server_name])
        count += 1
    ax.grid(which='both', axis='x')
    ax.legend(loc='upper center', shadow=True)
    plt.xlabel('Time to receive tile in seconds')
    plt.ylabel('Frequency')
    plt.title('Elapsed time to receive tiles ')

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    left_bar_pos = np.arange((num_bins - 1))

    count = 0
    legend_list = []
    for server_name in six.viewkeys(data):
        legend_list.append(
            mpatches.Patch(color=server_color[server_name], label=server_name))
        ax.bar(left_bar_pos, frequency_dict[server_name], count, zdir='y',
               width=1, label=server_name, color=server_color[server_name])
        count += 1
    ax.legend(handles=legend_list)
    ax.set_xticks(left_bar_pos)
    ax.set_xticklabels(interval)
    ax.grid(which='both', axis='x')
    ax.set_xlabel('Time to receive tile in seconds')
    ax.set_zlabel('Frequency')
    plt.title('Elapsed time to receive tiles ')

    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Plots data from each '
                                                 'file passed in')
    parser.add_argument('units', nargs=1,
                        help='choose s for files in seconds and choose m for'
                             ' files in miliseconds')
    parser.add_argument('elapsed_time', nargs='+', help='files to plot')
    args = parser.parse_args()

    main(args.elapsed_time, args.units[0])
