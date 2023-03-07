from pathlib import Path
from algorithm_sweep import AlgorithmSweep

import yaml

import large_image

VARIABLE_LAYERS = ["z", "c", "t"]


class AlgorithmSweepMultiSource(AlgorithmSweep):
    def initialize_storage(self):
        self.yaml_dict = {
            "name": f"{self.algorithm_name} iterative results",
            "description": f"{self.algorithm_name} algorithm performed on {self.input_filename}",
            "sources": [],
            "uniformSources": True,
        }
        param_desc = [
            f"{VARIABLE_LAYERS[i]} represents change in {n} as an index of {p}"
            if len(p) > 1 and i < len(VARIABLE_LAYERS)
            else f"{n} remains unchanged per run with a value of {p[0]}"
            for i, (n, p) in enumerate(self.input_params.items())
        ]
        if len(param_desc) > 0:
            self.yaml_dict["description"] += f', where {", ".join(param_desc)}'

    def apply_algorithm(self, param_combo):
        param_indices = {
            param_name: list(values).index(param_combo[index])
            for index, (param_name, values) in enumerate(self.input_params.items())
        }
        iteration_id = [param_indices[param_name] for param_name in self.param_order]
        filename = (
            f'{self.algorithm.__name__}_{"_".join([str(v) for v in iteration_id])}.tiff'
        )
        filepath = Path(self.output_dir, filename)

        desc = dict(
            **{"path": filename},
            **{VARIABLE_LAYERS[i]: v for i, v in enumerate(iteration_id)},
        )

        source = large_image.open(self.input_filename)
        new_source = large_image.new()
        for tile in source.tileIterator(
            format=large_image.tilesource.TILE_FORMAT_NUMPY,
            tile_size=dict(width=2048, height=2048),
        ):
            altered_data = self.algorithm(tile["tile"], *param_combo)
            new_source.addTile(altered_data, tile["x"], tile["y"])
        new_source.write(str(filepath), lossy=False)
        return desc

    def handle_result(self, result):
        self.yaml_dict["sources"].append(result)

    def complete_storage(self):
        with open(Path(self.output_dir, "results.yml"), "w") as f:
            yaml.dump(
                self.yaml_dict,
                f,
                default_flow_style=False,
                sort_keys=False,
            )
