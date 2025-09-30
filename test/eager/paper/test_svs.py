from test.eager.eager_helpers import run_eager_iterator_performance_testing_on_directory, run_reproducible_performance_evaluation

def test_svs():
    run_eager_iterator_performance_testing_on_directory(directory="./test_files/svs", file_extensions=[".svs"], output_file="./performance_testing.json")


if __name__ == "__main__":
    test_path = '/scr/arosado/tcga/acc/5b9efa00e62914002e94791c_TCGA-OR-A5LL-01Z-00-DX1.08588029-C532-4CDD-B945-251315EFF5C0.svs'
    run_reproducible_performance_evaluation(test_path, n_runs=10, output_dir="/scr/arosado/performance", without_cache=True)
    
    # run_eager_iterator_performance_testing_on_directory(directory="/scr/arosado/tcga", file_extensions=[".svs"], output_file="/scr/aroasdo/performance_test.json")