from pathlib import Path

import numpy as np
import xarray as xr
from algorithm_sweep import AlgorithmSweep

import large_image


class AlgorithmSweepXArray(AlgorithmSweep):
    def create_ds(self):
        dim_sizes = dict(
            **{k: len(v) for k, v in self.input_params.items()},
            **{
                "y": self.source_metadata["sizeY"],
                "x": self.source_metadata["sizeX"],
                "c": 4,
            },
        )

        ds = xr.Dataset(
            {
                "results": (
                    list(dim_sizes.keys()),
                    np.zeros(
                        tuple(dim_sizes.values()),
                    ),
                )
            },
            coords=self.input_params,
            attrs={
                "name": f"{self.algorithm_name} iterative results",
                "description": f"{self.algorithm_name} algorithm performed on {self.input_filename}",
            },
        )
        return ds

    def initialize_storage(self):
        self.source = large_image.open(self.input_filename)
        self.source_metadata = self.source.getMetadata()
        self.zarr_path = Path(self.output_dir, "results.zarr")
        ds = self.create_ds()
        ds.to_zarr(self.zarr_path, mode="w", compute=False)

    def apply_algorithm(self, param_combo):
        current_coords = {
            k: [param_combo[i]] for i, k in enumerate(self.input_params.keys())
        }
        output_data = np.empty(
            (
                self.source_metadata["sizeY"],
                self.source_metadata["sizeX"],
                4,
            )
        )
        for tile in self.source.tileIterator(
            format=large_image.tilesource.TILE_FORMAT_NUMPY,
            tile_size=dict(width=2048, height=2048),
        ):
            output_data[
                tile["y"]: tile["y"] + tile["height"],
                tile["x"]: tile["x"] + tile["width"],
            ] = self.algorithm(tile["tile"], *param_combo)

        output_ds = self.create_ds()
        output_ds["results"].loc[current_coords] = output_data

        current_index_region = {
            k: list(v.values).index(current_coords[k][0])
            for k, v in output_ds["results"].coords.items()
        }
        current_index_region_slice = {
            k: slice(i, i + 1) for k, i in current_index_region.items()
        }
        output_ds.isel(current_index_region_slice).to_zarr(
            self.zarr_path,
            mode="a",
            region=current_index_region_slice,
        )

    def handle_result(self, result):
        pass

    def complete_storage(self):
        ds = xr.open_zarr(self.zarr_path)
        print(ds)
