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


def create_argparser():
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
    argparser.add_argument(
        '-w',
        '--num_workers',
        required=False,
        default=4,
        type=int,
        help='Number of workers to use for processing algorithm iterations',
    )
    argparser.add_argument(
        '-p',
        '--param',
        action='append',
        required=False,
        nargs='*',
        help='A parameter to pass to the algorithm; '
             'instead of using the default value, '
             'Pass every item in the number space, '
             'specified as `--param=param_name,start,end,num_items[,open]`',
    )
    return argparser


def apply_algorithm(algorithm, input_filename, output_dir, params, param_space):
    iteration_id = [
        list(values).index(params[i]) for i, values in enumerate(param_space.values())
        if len(values) > 1
    ]
    filename = f'{algorithm.__name__}_{"_".join([str(v) for v in iteration_id])}.tiff'
    filepath = Path(output_dir, filename)

    desc = dict(
        **{'path': filename},
        **{VARIABLE_LAYERS[i]: v for i, v in enumerate(iteration_id)}
    )

    source = large_image.open(input_filename)
    new_source = large_image.new()
    for tile in source.tileIterator(
        format=large_image.tilesource.TILE_FORMAT_NUMPY,
        tile_size=dict(width=2048, height=2048),
    ):
        altered_data = algorithm(tile['tile'], *params)
    new_source.addTile(altered_data, tile['x'], tile['y'])
    new_source.write(str(filepath), lossy=False)
    return desc


def sweep_algorithm(algorithm, input_filename, input_params, output_dir, max_workers):
    algorithm_name = algorithm.__name__.replace('_', ' ').title()
    yaml_dict = {
        'name': f'{algorithm_name} iterative results',
        'description': f'{algorithm_name} algorithm performed on {input_filename}',
        'sources': [],
        'uniformSources': True,
    }
    param_desc = [
        f'{VARIABLE_LAYERS[i]} represents change in {n} as an index of {p}'
        if len(p) > 1 and i < len(VARIABLE_LAYERS)
        else f'{n} remains unchanged per run with a value of {p[0]}'
        for i, (n, p) in enumerate(input_params.items())
    ]
    if len(param_desc) > 0:
        yaml_dict['description'] += f', where {", ".join(param_desc)}'

    param_space_combos = list(itertools.product(*input_params.values()))
    print(f'Beginning {len(param_space_combos)} runs on {max_workers} workers...')
    num_done = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        # cannot pass source through submitted task; it is unpickleable
        futures = [
            executor.submit(
                apply_algorithm,
                algorithm,
                input_filename,
                output_dir,
                combo,
                input_params
            )
            for combo in param_space_combos
        ]
        for future in concurrent.futures.as_completed(futures):
            num_done += 1
            print(f'Completed {num_done} of {len(param_space_combos)} runs.')
            yaml_dict['sources'].append(future.result())

    with open(Path(output_dir, 'results.yml'), 'w') as f:
        yaml.dump(
            yaml_dict,
            f,
            default_flow_style=False,
            sort_keys=False,
        )


if __name__ == '__main__':
    argparser = create_argparser()
    args = argparser.parse_args()

    algorithm_code = args.algorithm_code
    input_filename = args.input_filename
    output_dir = args.output_dir
    max_workers = args.num_workers
    if args.param:
        input_params = {
            p[0].split(',')[0]: [i.strip() for i in p[0].split(',')[1:]]
            for p in args.param
        }
    else:
        input_params = {}
    input_params = {
        key: np.linspace(
            float(value[0]), float(value[1]), int(value[2]), endpoint=len(value) > 3
        )
        for key, value in input_params.items()
        if len(value) >= 3
    }

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

    params = {
        param.name: (
            input_params[param.name]
            if param.name in input_params
            else [param.default]
        )
        for param in sig.parameters.values()
    }

    del params['data']
    sweep_algorithm(algorithm, input_filename, params, output_dir, max_workers)
    print('Process complete.')
