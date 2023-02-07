from pathlib import Path
import large_image
import os
import yaml
import algorithms

input_images = [
    "data/sample_jp2k_33003_TCGA-CV-7242-11A-01-TS1.1838afb1-9eee-4a70-9ae3-50e3ab45e242.svs",
    "data/TCGA-02-0010-01Z-00-DX4.07de2e55-a8fe-40ee-9e98-bcb78050b9f7.svs",
    "data/TCGA-06-0129-01Z-00-DX3.bae772ea-dd36-47ec-8185-761989be3cc8.svs",
    "data/TCGA-AA-A02O-11A-01-BS1.8b76f05c-4a8b-44ba-b581-6b8b4f437367.svs",
]


def apply_algorithm(algorithm, source):
    new_source = large_image.new()
    for tile in source.tileIterator(
        format=large_image.tilesource.TILE_FORMAT_NUMPY,
        tile_size=dict(width=2048, height=2048),
    ):
        altered_data = algorithm(tile["tile"])
        new_source.addTile(altered_data, tile["x"], tile["y"])
    return new_source


def save_result(source, iteration, output_folder):
    filename = f"iteration_{iteration}.tiff"
    filepath = Path(output_folder, filename)
    source.write(filepath, lossy=False)
    return filename, iteration


def combine_results(results, output_folder, algorithm_name, input_image):
    yaml_dict = {
        "name": f"{algorithm_name.title()} iterative results",
        "description": f"Saved results from {len(results)} iterations of the \
            {algorithm_name} algorithm performed on {input_image}",
        "sources": [{"path": input_image}] + [
            {
                "path": r[0],
                "z": r[1],
            }
            for r in results
        ],
    }
    with open(Path(output_folder, "results.yml"), "w") as f:
        yaml.dump(
            yaml_dict,
            f,
            default_flow_style=False,
            sort_keys=False,
        )


def iterate_algorithm(input_image, algorithm, n):
    source = large_image.open(input_image)
    algorithm_name = algorithm.__name__
    output_folder = algorithm_name + "_output"
    if not Path(output_folder).exists():
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


if __name__ == "__main__":
    iterate_algorithm(
        input_images[0],
        algorithms.erode,
        n=5,
    )
