from pathlib import Path

import h5py
import numpy as np
from algorithm_sweep import AlgorithmSweep

import large_image


class AlgorithmSweepHDF5(AlgorithmSweep):
    def initialize_storage(self):
        self.output_files = []
        source = large_image.open(self.input_filename)
        self.source_metadata = source.getMetadata()

        self.filepath = Path(self.output_dir, 'results.h5')
        self.iteration_dims = {
            'y': self.source_metadata['sizeY'],
            'x': self.source_metadata['sizeX'],
            'c': 4,
        }
        self.param_dims = {k: len(v) for k, v in self.input_params.items()}
        self.layout = h5py.VirtualLayout(
            shape=tuple(dict(**self.param_dims, **self.iteration_dims).values()),
            dtype=int,
        )

    def __getstate__(self):
        # this method is called when you are
        # going to pickle the class, to know what to pickle
        state = self.__dict__.copy()

        # don't pickle the parameter fun.
        del state['layout']
        return state

    def apply_algorithm(self, param_combo):
        output_data = np.empty(
            (
                self.source_metadata['sizeY'],
                self.source_metadata['sizeX'],
                4,
            )
        )
        source = large_image.open(self.input_filename)
        for tile in source.tileIterator(
            format=large_image.tilesource.TILE_FORMAT_NUMPY,
            tile_size=dict(width=2048, height=2048),
        ):
            output_data[
                tile['y']: tile['y'] + tile['height'],
                tile['x']: tile['x'] + tile['width'],
            ] = self.algorithm(tile['tile'], *param_combo)
        return (output_data, param_combo)

    def handle_result(self, result, **kwargs):
        output_data, param_combo = result
        output_file = Path(
            self.output_dir, '{}.h5'.format('_'.join(str(v) for v in param_combo))
        )
        with h5py.File(output_file, 'w') as f:
            f.create_dataset(
                'data', tuple(self.iteration_dims.values()), 'i8', output_data
            )
        vsource = h5py.VirtualSource(
            output_file,
            'data',
            shape=tuple(self.iteration_dims.values()),
        )
        slice_index = tuple(
            list(v).index(param_combo[i])
            for i, v in enumerate(self.input_params.values())
        )
        self.layout[slice_index] = vsource

    def complete_storage(self):
        f = h5py.File(self.filepath, 'w', libver='latest')
        f.create_virtual_dataset('vdata', self.layout)
        for k, v in self.input_params.items():
            f['vdata'].attrs[k] = list(v)
        f.close()

        # Read it back
        with h5py.File(self.filepath, 'r') as f:
            print(f['vdata'][...])
            print(dict(f['vdata'].attrs))
