import argparse
import inspect
import os
from pathlib import Path

import algorithms
import numpy as np
from multisource_sweep import sweep_algorithm_multisource
from xarray_sweep import sweep_algorithm_xarray


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
        '-f',
        '--format',
        required=False,
        choices=['multisource', 'xarray', 'hdf5'],
        default='multisource',
        help='Storage mechanism and output format',
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


if __name__ == '__main__':
    argparser = create_argparser()
    args = argparser.parse_args()

    algorithm_code = args.algorithm_code
    input_filename = args.input_filename
    output_dir = args.output_dir
    output_format = args.format
    max_workers = args.num_workers

    sweep_function = sweep_algorithm_multisource
    if output_format == 'xarray':
        sweep_function = sweep_algorithm_xarray

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
    param_order = list(input_params.keys())

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
            input_params[param.name] if param.name in input_params else [param.default]
        )
        for param in sig.parameters.values()
    }

    del params['data']
    sweep_function(
        algorithm,
        input_filename,
        params,
        param_order,
        output_dir,
        max_workers,
    )
    print('Process complete.')
