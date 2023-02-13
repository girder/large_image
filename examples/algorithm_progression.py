import argparse
import concurrent.futures
import inspect
import itertools
import os
from pathlib import Path

import algorithms
import numpy as np
import yaml

import large_image

VARIABLE_LAYERS = ['z', 'c', 't']
MAX_THREADS = 4


argparser = argparse.ArgumentParser(
    prog='Algorithm Progression',
    description='Apply an algorithm to an input image '
    'for every parameter set in a given parameter space',
)
argparser.add_argument(
    'algorithm_code',
    choices=algorithms.ALGORITHM_CODES.keys(),
    help='Code to specify which of the available algorithms should be used',
)
argparser.add_argument('input_filename', help='Path to an image to use as input')
argparser.add_argument(
    '-o',
    '--output_dir',
    required=False,
    help='Name for a new directory in this location, wherein result images will be stored',
)


def apply_algorithm(algorithm, source, params):
    new_source = large_image.new()
    for tile in source.tileIterator(
        format=large_image.tilesource.TILE_FORMAT_NUMPY,
        tile_size=dict(width=2048, height=2048),
    ):
        altered_data = algorithm(tile['tile'], *params)
    new_source.addTile(altered_data, tile['x'], tile['y'])
    return new_source


def save_result(source, iteration, params, output_dir, algorithm_name):
    filename = f'{algorithm_name} {iteration}.tiff'
    filepath = Path(output_dir, filename)
    source.write(str(filepath), lossy=False)
    desc = {'path': filename}
    for i, v in enumerate(params):
        desc[VARIABLE_LAYERS[i]] = float(v)
    return desc


def sweep_algorithm(algorithm, input_filename, input_params, output_dir):
    algorithm_name = algorithm.__name__.replace('_', ' ').title()
    yaml_dict = {
        'name': f'{algorithm_name} iterative results',
        'description': f'{algorithm_name} algorithm performed on {input_filename}',
        'sources': [{'path': input_filename}],
    }
    param_desc = [
        f'{VARIABLE_LAYERS[i]} = {n}'
        for i, (n, p) in enumerate(input_params.items())
        if len(p) > 1 and i < len(VARIABLE_LAYERS)
    ]
    if len(param_desc) > 0:
        yaml_dict['description'] += f', where {", ".join(param_desc)}'

    source = large_image.open(input_filename)
    param_space_combos = itertools.product(*input_params.values())
    combos_uniques = itertools.product(
        *[p for p in input_params.values() if len(p) > 1]
    )

    print(f'Beginning {len(param_space_combos)} runs on {MAX_THREADS} threads...')
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        for result in executor.map(
            lambda combo, unique: save_result(
                apply_algorithm(algorithm, source, combo),
                *unique,
                output_dir,
                algorithm_name,
            ),
            param_space_combos,
            enumerate(combos_uniques),
        ):
            yaml_dict['sources'].append(result)

    with open(Path(output_dir, 'results.yml'), 'w') as f:
        yaml.dump(
            yaml_dict,
            f,
            default_flow_style=False,
            sort_keys=False,
        )


def get_input_params_from_user(algorithm, sig):
    print(f'\nProvide parameter space for algorithm {algorithm.__name__}.')
    print(
        'Hit enter to accept default for every run, '
        'provide a single value to replace the default for every run.'
    )
    print(
        'Provide two values separated by a comma '
        'to specify a range to cover across all runs.'
    )
    input_params = {}
    for param in sig.parameters.values():
        if param.name != 'data':
            user_input = input(f'{param.name} ({param.default}): ')
            if len(user_input.split(',')) == 2:
                user_range = [float(i.strip()) for i in user_input.split(',')]
                num_values = int(
                    input(
                        f'Enter a number of values to generate in the range {user_range}:'
                    )
                )
                input_params[param.name] = np.linspace(
                    user_range[0], user_range[1], num=num_values
                )
            elif len(user_input):
                input_params[param.name] = [user_input]
            else:
                input_params[param.name] = [param.default]
    return input_params


if __name__ == '__main__':
    args = argparser.parse_args()

    algorithm_code = args.algorithm_code
    input_filename = args.input_filename
    output_dir = args.output_dir

    if not Path(input_filename).exists():
        raise ValueError(f'Cannot locate file {input_filename}.')

    algorithm = algorithms.ALGORITHM_CODES[algorithm_code]
    sig = inspect.signature(algorithm)

    if not output_dir:
        output_dir = f'{algorithm.__name__}_output'
        i = 0
        while Path(output_dir).exists():
            i += 1
            output_dir = f'{algorithm.__name__}_output_{i}'
        os.mkdir(output_dir)
    else:
        if not Path(output_dir).exists():
            os.mkdir(output_dir)

    user_provided = input(
        'Hit enter to use default parameter space, enter anything to provide your own: '
    )
    if user_provided:
        input_params = get_input_params_from_user(algorithm, sig)
    else:
        input_params = {
            param.name: (
                [param.default]
                if param.name
                not in algorithms.ALGORITHM_DEFAULT_PARAM_SPREADS[algorithm_code]
                else algorithms.ALGORITHM_DEFAULT_PARAM_SPREADS[algorithm_code][
                    param.name
                ]
            )
            for param in sig.parameters.values()
        }

    del input_params['data']
    sweep_algorithm(algorithm, input_filename, input_params, output_dir)
    print('Process complete.')
