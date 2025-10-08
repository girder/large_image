import sys
import os
import numpy as np
import torch
from matplotlib import pyplot as plt
from torchvision.transforms import v2

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

sys.path.append(base_path)

from test.eager.eager_helpers import run_eager_iterator_performance_testing_on_directory, run_reproducible_performance_evaluation

def write_transform(image, x: int, y: int):
    if x > -1 and y > -1:
        plt.imsave(f"/scr/arosado/performance/write_transform/image_{x}_{y}.png", image)
        return image
    else:
        return image

def test_write_transform(test_path):
    # run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/write", without_cache=False, only_eager=False, performance_type='write', transform=write_transform)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/write_transform_eager_multiprocessing", without_cache=False, only_eager=True, performance_type='write_multiprocessing')

def test_without_icc(test_path):
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/without_icc", without_cache=True, only_eager=False, without_icc=True)

def test_prefetch_workers(test_path):
    # run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/1", without_cache=False, only_eager=True, prefetch=1, workers=1)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/2", without_cache=False, only_eager=True, prefetch=2, workers=2)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/3", without_cache=False, only_eager=True, prefetch=3, workers=3)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/4", without_cache=False, only_eager=True, prefetch=4, workers=4)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/8", without_cache=False, only_eager=True, prefetch=8, workers=8)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/12", without_cache=False, only_eager=True, prefetch=12, workers=12)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/16", without_cache=False, only_eager=True, prefetch=16, workers=16)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/20", without_cache=False, only_eager=True, prefetch=20, workers=20)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/28", without_cache=False, only_eager=True, prefetch=28, workers=28)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/24", without_cache=False, only_eager=True, prefetch=24, workers=24)   
    

def test_chunk_size(test_path):
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/1", without_cache=False, only_eager=True, chunk_mult=1)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/2", without_cache=False, only_eager=True, chunk_mult=2)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/3", without_cache=False, only_eager=True, chunk_mult=3)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/4", without_cache=False, only_eager=True, chunk_mult=4)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/5", without_cache=False, only_eager=True, chunk_mult=5)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/6", without_cache=False, only_eager=True, chunk_mult=6)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/7", without_cache=False, only_eager=True, chunk_mult=7)

def test_svs(test_path):
    run_eager_iterator_performance_testing_on_directory(directory="./test_files/svs", file_extensions=[".svs"], output_file="./performance_testing.json")


def test_batch_size(test_path):
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/batch_size/64", without_cache=False, only_eager=True, batch=64)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/batch_size/128", without_cache=False, only_eager=True, batch=128)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/batch_size/256", without_cache=False, only_eager=True, batch=256)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/batch_size/512", without_cache=False, only_eager=True, batch=512)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/batch_size/1024", without_cache=False, only_eager=True, batch=1024)


def test_svs_default(test_path):
    run_reproducible_performance_evaluation(test_path, n_runs=10, output_dir="/scr/arosado/performance/default", without_cache=True)


def test_svs_tile_overlap(test_path):
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/25", without_cache=False, tile_overlap={'x': 25, 'y': 25})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/50", without_cache=False, tile_overlap={'x': 50, 'y': 50})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/75", without_cache=False, tile_overlap={'x': 75, 'y': 75})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/120", without_cache=False, tile_overlap={'x': 120, 'y': 120})


def test_svs_mag_resolution(test_path):
    # Test performance with different resolutions
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/mag_resolution/1x", without_cache=False, scale={'magnification':  1})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/mag_resolution/2.5x", without_cache=False, scale={'magnification':  2.5})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/mag_resolution/5x", without_cache=False, scale={'magnification':  5})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/mag_resolution/10x", without_cache=False, scale={'magnification':  10})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/mag_resolution/20x", without_cache=False, scale={'magnification':  20})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/mag_resolution/40x", without_cache=False, scale={'magnification':  40})

    
def test_svs_mm_resolution(test_path):
    # Test performance with different resolutions
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/mm_resolution/mm_1x", without_cache=False, scale={'mm_x':  0.00025*2*2*2*5, 'mm_y': 0.00025*2*2*2*5})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/mm_resolution/mm_2.5x", without_cache=False, scale={'mm_x':  0.00025*2*2*2*2, 'mm_y': 0.00025*2*2*2*2})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/mm_resolution/mm_5x", without_cache=False, scale={'mm_x':  0.00025*2*2*2, 'mm_y': 0.00025*2*2*2})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/mm_resolution/mm_10x", without_cache=False, scale={'mm_x':  0.00025*2*2, 'mm_y': 0.00025*2*2})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/mm_resolution/mm_20x", without_cache=False, scale={'mm_x':  0.00025*2, 'mm_y': 0.00025*2})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/mm_resolution/mm_40x", without_cache=False, scale={'mm_x':  0.00025, 'mm_y': 0.00025})

def test_svs_tile_size(test_path):
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_size/96", without_cache=False, tile_size={'width': 96, 'height': 96})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_size/128", without_cache=False, tile_size={'width': 128, 'height': 128})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_size/224", without_cache=False, tile_size={'width': 224, 'height': 224})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_size/240", without_cache=False, tile_size={'width': 240, 'height': 240})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_size/256", without_cache=False, tile_size={'width': 256, 'height': 256})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_size/512", without_cache=False, tile_size={'width': 512, 'height': 512})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_size/1024", without_cache=False, tile_size={'width': 1024, 'height': 1024})


def test_svs_with_tiff_source(test_path):
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/with_tiff_source", without_cache=True, only_eager=False, with_tiff_source=True)

def test_svs_with_efficientnet(test_path):
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/with_efficientnet", without_cache=False, only_eager=True, performance_type='inference_efficientnetb0')


def test_svs_with_pytorch_transform(test_path):
    # transform = v2.Compose([
    #     v2.ToImage(),
    #     v2.RandomResizedCrop(size=(288, 288), antialias=True),
    #     v2.RandomHorizontalFlip(p=0.5),
    #     v2.ToDtype(torch.float32, scale=True),
    #     v2.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    # ])

    transform = v2.Compose(
        [
            v2.Resize(224),
            v2.ToTensor(),
            v2.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )

    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/with_pytorch_transform", without_cache=False, only_eager=True, performance_type='pytorch_transform', transform=transform)


def test_svs_sobel(test_path):
    transform = v2.Compose(
        [
            v2.Resize(224),
            v2.ToTensor(),
            v2.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/sobel", without_cache=False, only_eager=False, performance_type='inference_sobel', transform=transform)

if __name__ == "__main__":
    test_path = '/scr/arosado/tcga/acc/5b9efa00e62914002e94791c_TCGA-OR-A5LL-01Z-00-DX1.08588029-C532-4CDD-B945-251315EFF5C0.svs'

    # Test performance with default settings
    # test_svs_default()

    # Test performance with different tile overlaps
    # test_svs_tile_overlap()

    # Test performance with different resolutions
    # test_svs_mag_resolution()

    # Test performance with different batch sizes
    # test_batch_size()

    # Test performance with different chunk sizes
    #test_chunk_size()

    # Test performance without ICC correction
    # test_without_icc()

    # Test performance with different prefetch and workers
    # test_prefetch_workers()

    # Test performance with different tile sizes
    # test_svs_tile_size()

    # Test performance with tiff source
    # test_svs_with_tiff_source()

    # Test performance with write transform
    # test_write_transform(test_path)

    # Test performance with pytorch transform
    test_svs_with_pytorch_transform(test_path)

    # Test performance with sobel
    # test_svs_sobel(test_path)

    pass

    # run_eager_iterator_performance_testing_on_directory(directory="/scr/arosado/tcga", file_extensions=[".svs"], output_file="/scr/aroasdo/performance_test.json")