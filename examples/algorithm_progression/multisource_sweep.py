import concurrent.futures
import itertools
from pathlib import Path

import yaml

import large_image

VARIABLE_LAYERS = ['z', 'c', 't']


def apply_algorithm_multisource(
    algorithm,
    input_filename,
    output_dir,
    params,
    param_space,
    param_order,
):
    param_indices = {
        param_name: list(values).index(params[index])
        for index, (param_name, values) in enumerate(param_space.items())
    }
    iteration_id = [param_indices[param_name] for param_name in param_order]
    filename = f'{algorithm.__name__}_{"_".join([str(v) for v in iteration_id])}.tiff'
    filepath = Path(output_dir, filename)

    desc = dict(
        **{'path': filename},
        **{VARIABLE_LAYERS[i]: v for i, v in enumerate(iteration_id)},
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


def sweep_algorithm_multisource(
    algorithm,
    input_filename,
    input_params,
    param_order,
    output_dir,
    max_workers,
):
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
                apply_algorithm_multisource,
                algorithm,
                input_filename,
                output_dir,
                combo,
                input_params,
                param_order,
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
