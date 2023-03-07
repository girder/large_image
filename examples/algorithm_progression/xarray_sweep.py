from pathlib import Path

import numpy as np
import xarray as xr
from algorithm_sweep import AlgorithmSweep

import large_image


class AlgorithmSweepXArray(AlgorithmSweep):
    def initialize_storage(self):
        self.output_files = []

    def apply_algorithm(self, param_combo):
        iteration_filename = (
            Path(self.output_dir) / f'result_{"_".join(str(v) for v in param_combo)}.nc'
        )
        if not iteration_filename.exists():
            current_coords = {
                k: [param_combo[i]] for i, k in enumerate(self.input_params.keys())
            }
            source = large_image.open(self.input_filename)
            source_metadata = source.getMetadata()
            output_data = np.empty(
                (
                    source_metadata["sizeY"],
                    source_metadata["sizeX"],
                    4,
                )
            )
            for tile in source.tileIterator(
                format=large_image.tilesource.TILE_FORMAT_NUMPY,
                tile_size=dict(width=2048, height=2048),
            ):
                output_data[
                    tile["x"]: tile["x"] + tile["width"],
                    tile["y"]: tile["y"] + tile["height"],
                ] = self.algorithm(tile["tile"], *param_combo)

            xr.DataArray(
                output_data,
                dims=["y", "x", "c"],
                attrs=current_coords,
            ).to_netcdf(iteration_filename)
        return iteration_filename

    def handle_result(self, result):
        self.output_files.append(result)

    def complete_storage(self):
        results = [xr.open_dataarray(filename) for filename in self.output_files]
        if len(results) > 0:
            dims = dict(
                **{k: len(v) for k, v in self.input_params.items()},
                **results[0].sizes,
            )
            composite_xr = xr.DataArray(
                np.empty(tuple(dims.values())),
                coords=self.input_params,
                dims=dims,
            )

            for result in results:
                composite_xr.loc[result.attrs] = result.astype(int)
            composite_xr.to_netcdf(Path(self.output_dir, "results.nc"))
            for output_filename in self.output_files:
                output_filename.unlink()
