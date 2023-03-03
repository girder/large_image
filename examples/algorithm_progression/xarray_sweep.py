import concurrent.futures
import itertools

import dask.array as da
import xarray as xr
from dask.diagnostics import ProgressBar

import large_image


def apply_algorithm_xarray(
    algorithm,
    input_filename,
    params,
):
    source = large_image.open(input_filename)
    new_source = large_image.new()
    for tile in source.tileIterator(
        format=large_image.tilesource.TILE_FORMAT_NUMPY,
        tile_size=dict(width=2048, height=2048),
    ):
        altered_data = algorithm(tile["tile"], *params)
        new_source.addTile(altered_data, tile["x"], tile["y"])
    return params, new_source.getRegion(format=large_image.constants.TILE_FORMAT_NUMPY)


def sweep_algorithm_xarray(
    algorithm,
    input_filename,
    input_params,
    param_order,
    output_dir,
    max_workers,
):
    algorithm_name = algorithm.__name__.replace("_", " ").title()
    source = large_image.open(input_filename)
    source_metadata = source.getMetadata()

    structure_shape = [len(values) for values in input_params.values()] + [
        source_metadata["sizeY"],
        source_metadata["sizeX"],
        4,
    ]
    structure = xr.DataArray(
        da.zeros(tuple(structure_shape)),
        coords=input_params,
        dims=list(input_params.keys()) + ["y", "x", "c"],
        attrs={
            "algorithm": algorithm_name,
            "input_filename": input_filename,
        },
    )

    param_space_combos = list(itertools.product(*input_params.values()))
    print(f"Beginning {len(param_space_combos)} runs on {max_workers} workers...")
    num_done = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        # cannot pass source through submitted task; it is unpickleable
        futures = [
            executor.submit(
                apply_algorithm_xarray,
                algorithm,
                input_filename,
                combo,
            )
            for combo in param_space_combos
        ]
        for future in concurrent.futures.as_completed(futures):
            num_done += 1
            print(f"Completed {num_done} of {len(param_space_combos)} runs.")
            param_combo, output_data = future.result()
            current_coords = {
                k: param_combo[i] for i, k in enumerate(input_params.keys())
            }
            structure.loc[current_coords] = output_data[0]

    delayed_write_operation = structure.to_netcdf(
        output_dir + "/results.nc", compute=False
    )
    print(f"Writing results to {output_dir}...")
    with ProgressBar():
        delayed_write_operation.compute()
