import sys
import os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

sys.path.append(base_path)

from test.eager.eager_helpers import run_eager_iterator_performance_testing_on_directory, run_reproducible_performance_evaluation

def test_svs():
    run_eager_iterator_performance_testing_on_directory(directory="./test_files/svs", file_extensions=[".svs"], output_file="./performance_testing.json")


def test_svs_default():
    run_reproducible_performance_evaluation(test_path, n_runs=10, output_dir="/scr/arosado/performance/default", without_cache=True)


def test_svs_tile_overlap():
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/25", without_cache=False, tile_overlap={'x': 25, 'y': 25})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/50", without_cache=False, tile_overlap={'x': 50, 'y': 50})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/75", without_cache=False, tile_overlap={'x': 75, 'y': 75})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/120", without_cache=False, tile_overlap={'x': 120, 'y': 120})


def test_svs_resolution():
    # Test performance with different resolutions
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/resolution/1x", without_cache=False, scale={'magnification':  1})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/resolution/2.5x", without_cache=False, scale={'magnification':  2.5})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/resolution/5x", without_cache=False, scale={'magnification':  5})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/resolution/10x", without_cache=False, scale={'magnification':  10})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/resolution/20x", without_cache=False, scale={'magnification':  20})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/resolution/40x", without_cache=False, scale={'magnification':  40})

    # Test performance with different resolutions
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/resolution/mm_1x", without_cache=False, scale={'mm_x':  0.00025*2*2*2*5, 'mm_y': 0.00025*2*2*2*5})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/resolution/mm_2.5x", without_cache=False, scale={'mm_x':  0.00025*2*2*2*2, 'mm_y': 0.00025*2*2*2*2})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/resolution/mm_5x", without_cache=False, scale={'mm_x':  0.00025*2*2*2, 'mm_y': 0.00025*2*2*2})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/resolution/mm_10x", without_cache=False, scale={'mm_x':  0.00025*2*2, 'mm_y': 0.00025*2*2})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/resolution/mm_20x", without_cache=False, scale={'mm_x':  0.00025*2, 'mm_y': 0.00025*2})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/resolution/mm_40x", without_cache=False, scale={'mm_x':  0.00025, 'mm_y': 0.00025})


if __name__ == "__main__":
    test_path = '/scr/arosado/tcga/acc/5b9efa00e62914002e94791c_TCGA-OR-A5LL-01Z-00-DX1.08588029-C532-4CDD-B945-251315EFF5C0.svs'

    # Test performance with default settings
    # test_svs_default()

    # Test performance with different tile overlaps
    test_svs_tile_overlap()

    # Test performance with different resolutions
    # test_svs_resolution()

    pass

    # run_eager_iterator_performance_testing_on_directory(directory="/scr/arosado/tcga", file_extensions=[".svs"], output_file="/scr/aroasdo/performance_test.json")