import concurrent.futures
import itertools


class AlgorithmSweep:
    def __init__(
        self,
        algorithm,
        input_filename,
        input_params,
        param_order,
        output_dir,
        max_workers,
    ):
        self.algorithm = algorithm
        self.input_filename = input_filename
        self.input_params = input_params
        self.param_order = param_order
        self.output_dir = output_dir
        self.max_workers = max_workers

        self.algorithm_name = algorithm.__name__.replace('_', ' ').title()
        self.param_space_combos = list(itertools.product(*input_params.values()))

        self.initialize_storage()

    def sweep(self):
        print(
            f'Beginning {len(self.param_space_combos)} runs on {self.max_workers} workers...'
        )
        num_done = 0
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            # cannot pass source through submitted task; it is unpickleable
            futures = [
                executor.submit(
                    self.apply_algorithm,
                    combo,
                )
                for combo in self.param_space_combos
            ]
            for future in concurrent.futures.as_completed(futures):
                num_done += 1
                print(f'Completed {num_done} of {len(self.param_space_combos)} runs.')
                self.handle_result(future.result())
        self.complete_storage()

    def initialize_storage(self):
        raise NotImplementedError()

    def apply_algorithm(self, param_combo):
        raise NotImplementedError()

    def handle_result(self, result):
        raise NotImplementedError()

    def complete_storage(self):
        raise NotImplementedError()
