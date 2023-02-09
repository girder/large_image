import itertools
import os
import pathlib
import shutil
import sys

import algorithms
import numpy
import yaml

import large_image


def apply_algorithm(algorithm, source, params):
    new_source = large_image.new()
    for tile in source.tileIterator(
        format=large_image.tilesource.TILE_FORMAT_NUMPY,
        tile_size=dict(width=2048, height=2048),
    ):
        altered_data = algorithm(tile['tile'], **params)
        new_source.addTile(altered_data, tile['x'], tile['y'])
    return new_source


def save_result(source, iteration, output_folder):
    filename = f'iteration_{iteration if isinstance(iteration, int) else "_".join(str(v) for v in iteration)}.tiff'  # noqa
    filepath = pathlib.Path(output_folder, filename)
    source.write(str(filepath), lossy=False)
    return filename, iteration


def combine_results(results, output_folder, algorithm_name, input_image):
    base = os.path.basename(input_image)
    shutil.copy(input_image, pathlib.Path(output_folder, base))
    yaml_dict = {
        'name': f'{algorithm_name.title()} iterative results',
        'description':
            f'Saved results from {len(results)} iterations of ' +
            f'the {algorithm_name} algorithm performed on {input_image}',
        'sources': [{'path': base}],
    }
    if len(results[0][1]) == 1:
        yaml_dict['sources'] += [
            {
                'path': r[0],
                'z': r[1][0] + 1,
            }
            for r in results
        ]
    else:
        yaml_dict['sources'] = []
        for r in results:
            entry = {'path': r[0]}
            for idx, key in enumerate(['z', 't', 'xy', 'c'][:len(r[1])]):
                entry[key] = r[1][idx]
            yaml_dict['sources'].append(entry)
    with open(pathlib.Path(output_folder, 'results.yml'), 'w') as f:
        yaml.dump(
            yaml_dict,
            f,
            default_flow_style=False,
            sort_keys=False,
        )


def iterate_algorithm(input_image, algorithm, n):
    source = large_image.open(input_image)
    algorithm_name = algorithm.__name__
    output_folder = algorithm_name + '_output'
    if not pathlib.Path(output_folder).exists():
        os.mkdir(output_folder)

    results = []
    for i in range(n):
        source = apply_algorithm(algorithm, source)
        results.append(
            save_result(
                source,
                i + 1,
                output_folder,
            )
        )
    combine_results(
        results,
        output_folder,
        algorithm_name,
        input_image,
    )


def apply_and_result(module, algname, input_image, paramlist, output_folder):
    source = large_image.open(input_image)
    algorithm = getattr(__import__(module), algname)
    alparams = {entry[1]: entry[2] for entry in paramlist}
    print(alparams)
    output = apply_algorithm(algorithm, source, alparams)
    result = save_result(
        output,
        [entry[0] for entry in paramlist],
        output_folder,
    )
    return result


def sweep_algorithm(input_image, algorithm, params):
    """
    See:

    params = [('key1', [values1]), ('key2', [values2]), ...]
    """
    algorithm_name = algorithm.__name__
    output_folder = algorithm_name + '_output'
    if not pathlib.Path(output_folder).exists():
        os.mkdir(output_folder)
    print(output_folder)

    lists = [
        [(idx, param[0], val) for idx, val in enumerate(param[1])]
        for param in params
    ]
    # pass the algorithm module and name here to make it possible to do this
    # more flexibly in the future.
    results = [
        apply_and_result('algorithms', algorithm_name, input_image, paramlist, output_folder)
        for paramlist in itertools.product(*lists)]

    combine_results(
        results,
        output_folder,
        algorithm_name,
        input_image,
    )


if __name__ == '__main__':
    args = sys.argv[1:]
    filename = args[0]
    """
    iterate_algorithm(
        filename,
        algorithms.erode,
        n=5,
    )
    """
    sweep_algorithm(
        filename,
        algorithms.positive_pixel_count,
        params=[
            ('hue_value', numpy.linspace(0, 1, 20, endpoint=False)),
            # ('hue_width', numpy.linspace(0.05, 0.25, 5)),
            # ('hue_value', numpy.linspace(0, 1, 256, endpoint=False)),
            ('hue_width', numpy.linspace(0.15, 0.15, 1)),
            # ('hue_value', numpy.linspace(0, 1, 250, endpoint=False)),
            # ('hue_width', numpy.linspace(0.05, 0.25, 9)),
        ],
    )
