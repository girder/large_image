import argparse
import concurrent.futures
import inspect
import itertools
import os
import sys
import time
from pathlib import Path

try:
    import algorithms
except ImportError:
    from . import algorithms
import large_image_source_vips
import large_image_source_zarr
import numpy as np
import yaml

import large_image


class SweepAlgorithm:
    def __init__(self, algorithm, input_filename, input_params, param_order,
                 output_filename, max_workers, multiprocessing):
        self.algorithm = algorithm
        self.input_filename = input_filename
        self.output_filename = output_filename
        self.input_params = input_params
        self.param_order = param_order
        self.max_workers = max_workers
        self.multiprocessing = multiprocessing

        self.combos = list(itertools.product(*[p['range'] for p in input_params.values()]))

    def getOverallSink(self):
        msg = 'Not implemented'
        raise Exception(msg)

    def getTileSink(self, sink):
        msg = 'Not implemented'
        raise Exception(msg)

    def writeTileSink(self, tilesink, iteration_id):
        msg = 'Not implemented'
        raise Exception(msg)

    def writeOverallSink(self, sink):
        msg = 'Not implemented'
        raise Exception(msg)

    def collectResult(self, result):
        msg = 'Not implemented'
        raise Exception(msg)

    def addTile(self, tilesink, *args, **kwargs):
        return tilesink.addTile(*args, **kwargs)

    def applyAlgorithm(self, sink, params):
        source = large_image.open(self.input_filename)
        param_indices = {
            param_name: list(values['range']).index(params[index])
            for index, (param_name, values) in enumerate(self.input_params.items())
        }
        iteration_id = [param_indices[param_name] for param_name in self.param_order]
        tilesink = self.getTileSink(sink)
        for tile in source.tileIterator(
            format=large_image.tilesource.TILE_FORMAT_NUMPY,
            tile_size=dict(width=2048, height=2048),
        ):
            altered_data = self.algorithm(tile['tile'], *params)
            self.addTile(
                tilesink,
                altered_data, tile['x'], tile['y'],
                **{p['axis']: iteration_id[i] for i, p in enumerate(self.param_order.values())})
        return self.writeTileSink(tilesink, iteration_id)

    def run(self):
        starttime = time.time()
        sink = self.getOverallSink()

        print(f'Beginning {len(self.combos)} runs on {self.max_workers} workers...')
        num_done = 0
        poolExecutor = (
            concurrent.futures.ProcessPoolExecutor if self.multiprocessing else
            concurrent.futures.ThreadPoolExecutor)
        with poolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(
                    self.applyAlgorithm,
                    sink,
                    combo,
                )
                for combo in self.combos
            ]
            for future in concurrent.futures.as_completed(futures):
                self.collectResult(future.result())
                num_done += 1
                sys.stdout.write(f'Completed {num_done} of {len(self.combos)} runs.\r')
                sys.stdout.flush()
        print(f'Generation time {time.time() - starttime:5.3f}        ')
        starttime = time.time()
        self.writeOverallSink(sink)
        print(f'Save time {time.time() - starttime:5.3f}')


class SweepAlgorithmMulti(SweepAlgorithm):
    def getOverallSink(self):
        os.makedirs(self.output_filename, exist_ok=True)
        algorithm_name = self.algorithm.__name__.replace('_', ' ').title()
        self.yaml_dict = {
            'name': f'{algorithm_name} iterative results',
            'description': f'{algorithm_name} algorithm performed on {self.input_filename}',
            'axes': [p['axis'] for p in self.param_order.values()],
            'sources': [],
            'uniformSources': True,
        }
        return True

    def writeOverallSink(self, sink):
        with open(Path(self.output_filename, 'results.yml'), 'w') as f:
            yaml.dump(
                self.yaml_dict,
                f,
                default_flow_style=False,
                sort_keys=False,
            )

    def writeTileSink(self, tilesink, iteration_id):
        filename = f'{self.algorithm.__name__}_{"_".join([str(v) for v in iteration_id])}.tiff'
        filepath = Path(self.output_filename, filename)

        desc = dict(
            path=filename,
            **{p['axis']: iteration_id[i] for i, p in enumerate(self.param_order.values())},
        )
        tilesink.write(str(filepath), lossy=False)
        return desc

    def addTile(self, tilesink, *args, **kwargs):
        return tilesink.addTile(*args)

    def collectResult(self, result):
        self.yaml_dict['sources'].append(result)


class SweepAlgorithmMultiVips(SweepAlgorithmMulti):
    def getTileSink(self, sink):
        return large_image_source_vips.new()


class SweepAlgorithmMultiZarr(SweepAlgorithmMulti):
    def getTileSink(self, sink):
        return large_image_source_zarr.new()


class SweepAlgorithmZarr(SweepAlgorithm):
    def getOverallSink(self):
        return large_image_source_zarr.new()

    def writeOverallSink(self, sink):
        sink.write(self.output_filename, lossy=False)

    def getTileSink(self, sink):
        return sink

    def writeTileSink(self, tilesink, iteration_id):
        pass

    def collectResult(self, result):
        pass


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
        'output_filename',
        help='Name for output file or directory',
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
        '--multiprocessing',
        '--process',
        '--mp',
        action='store_true',
        help='Use multiprocessing for workers',
    )
    argparser.add_argument(
        '--threading',
        '--thread',
        '--mt',
        dest='multiprocessing',
        action='store_false',
        help='Use threading for workers',
    )
    argparser.add_argument(
        '--sink',
        required=False,
        default='zarr',
        help='Either zarr, multizarr, or multivips',
    )
    argparser.add_argument(
        '-p',
        '--param',
        action='append',
        required=False,
        help='A parameter to pass to the algorithm; instead of using the '
             'default value, Pass every item in the number space, specified '
             'as `--param=param_name,[axis_name,]start,end,num_items[,open]`',
    )
    return argparser


def main(argv):
    argparser = create_argparser()
    args = argparser.parse_args(argv[1:])

    algorithm_code = args.algorithm_code
    input_filename = args.input_filename
    input_params = {}
    defaultAxes = ['z', 'c', 't']
    axesUsed = set()
    for p in args.param or []:
        parts = [i.strip() for i in p.split(',')]
        rangevals = (parts[1:] if parts[1].isdigit() else parts[2:]) + ['']
        input_params[parts[0]] = {
            'param': parts[0],
            'axis': (
                (defaultAxes[0] if len(defaultAxes) else parts[0])
                if parts[1].isdigit() else parts[1]),
            'range': np.linspace(
                float(rangevals[0]), float(rangevals[1]),
                int(rangevals[2]), endpoint=bool(rangevals[3])),
        }
        axesUsed.add(input_params[parts[0]]['axis'].lower())
        if input_params[parts[0]]['axis'].lower() in defaultAxes:
            defaultAxes.remove(input_params[parts[0]]['axis'].lower())

    if not Path(input_filename).exists():
        msg = f'Cannot locate file {input_filename}.'
        raise ValueError(msg)

    algorithm = algorithms.ALGORITHM_CODES[algorithm_code]
    sig = inspect.signature(algorithm)

    params = {
        param.name: (
            input_params[param.name]
            if param.name in input_params
            else {
                'param': param.name,
                'axis': getattr(param, 'axis', param.name),
                'range': [param.default]}
        )
        for param in sig.parameters.values() if param.name != 'data'
    }

    # Use args.sink to pick class
    cls = {
        'multivips': SweepAlgorithmMultiVips,
        'zarr': SweepAlgorithmZarr,
        'multizarr': SweepAlgorithmMultiZarr,
    }[args.sink]

    sweep = cls(algorithm, input_filename, params, input_params,
                args.output_filename, args.num_workers, args.multiprocessing)
    sweep.run()


if __name__ == '__main__':
    main(sys.argv)
