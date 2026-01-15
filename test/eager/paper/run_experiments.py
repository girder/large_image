import sys
import os
from tkinter import FALSE
import numpy as np
import torch
from matplotlib import pyplot as plt
import albumentations as A
from torchvision.transforms import v2

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

sys.path.append(base_path)

from test.eager.eager_helpers import run_reproducible_performance_evaluation, run_performance_testing_on_directory

def write_transform(image, x: int, y: int):
    if x > -1 and y > -1:
        plt.imsave(f"/scr/arosado/performance/write/eager/transform/images/image_{x}_{y}.png", image)
        return image
    else:
        return image

def test_read_high_performance(test_path):
    # Run performance evaluation with high performance settings
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/read_high_performance/2", without_cache=False, run_eager=True, performance_type='read', prefetch=16, workers=64, chunk_mult=2)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/read_high_performance/4", without_cache=False, run_eager=True, performance_type='read', prefetch=16, workers=64, chunk_mult=4)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/read_high_performance/8", without_cache=False, run_eager=True, performance_type='read', prefetch=16, workers=64, chunk_mult=8)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/read_high_performance/16", without_cache=False, run_eager=True, performance_type='read', prefetch=16, workers=64, chunk_mult=16)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/read_high_performance/32", without_cache=False, run_eager=True, performance_type='read', prefetch=16, workers=64, chunk_mult=32)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/read_high_performance/64", without_cache=False, run_eager=True, performance_type='read', prefetch=16, workers=64, chunk_mult=64)


def test_read(test_path, file_dir):
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/read/dataset", without_cache=True, run_dataset=True, performance_type='read')
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/read/eager", without_cache=True, run_eager=True, performance_type='read')
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/read/non_eager", without_cache=True, run_eager=False, run_non_eager=True, performance_type='read')

def test_write(test_path):
    # run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/write/eager/default", without_cache=False, run_eager=True, performance_type='write')
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/write/eager/multiprocessing", without_cache=False, run_eager=True, performance_type='write_multiprocessing')
    # run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/write/non_eager/default", without_cache=False, run_eager=False, run_non_eager=True, performance_type='write')
    # run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/write/non_eager/multiprocessing", without_cache=False, run_eager=False, run_non_eager=True, performance_type='write_multiprocessing')
    # # Make directory for images to be written to
    # os.makedirs("/scr/arosado/performance/write/eager/transform/images", exist_ok=True)
    # run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/write/eager/transform", without_cache=False, run_eager=True, performance_type='write_transform', transform=write_transform)


def test_write_transform(test_path):
    # run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/write", without_cache=False, only_eager=False, performance_type='write', transform=write_transform)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/write_transform_eager_multiprocessing", without_cache=False, only_eager=True, performance_type='write_multiprocessing')

def test_without_icc(test_path):
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/without_icc", without_cache=True, only_eager=False, without_icc=True)

def test_prefetch_workers(test_path):
    # run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/1", without_cache=False, only_eager=True, prefetch=1, workers=1)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/2", without_cache=False, run_eager=True, prefetch=2, workers=2)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/3", without_cache=False, run_eager=True, prefetch=3, workers=3)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/4", without_cache=False, run_eager=True, prefetch=4, workers=4)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/8", without_cache=False, run_eager=True, prefetch=8, workers=8)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/12", without_cache=False, run_eager=True, prefetch=12, workers=12)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/16", without_cache=False, run_eager=True, prefetch=16, workers=16)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/20", without_cache=False, run_eager=True, prefetch=20, workers=20)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/28", without_cache=False, run_eager=True, prefetch=28, workers=28)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch_workers/24", without_cache=False, run_eager=True, prefetch=24, workers=24)


def test_prefetch(test_path, file_dir=None):
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch/eager/2", without_cache=False, run_eager=True, prefetch=2, workers=2)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch/eager/4", without_cache=False, run_eager=True, prefetch=4, workers=4)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch/eager/8", without_cache=False, run_eager=True, prefetch=8, workers=8)   
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch/eager/12", without_cache=False, run_eager=True, prefetch=12, workers=12)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch/eager/16", without_cache=False, run_eager=True, prefetch=16, workers=16)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch/eager/20", without_cache=False, run_eager=True, prefetch=20, workers=20)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch/eager/24", without_cache=False, run_eager=True, prefetch=24, workers=24)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch/eager/28", without_cache=False, run_eager=True, prefetch=28, workers=28)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch/eager/32", without_cache=False, run_eager=True, prefetch=32, workers=32)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch/eager/40", without_cache=False, run_eager=True, prefetch=40, workers=40)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch/eager/48", without_cache=False, run_eager=True, prefetch=48, workers=48)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch/eager/56", without_cache=False, run_eager=True, prefetch=56, workers=56)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/prefetch/eager/64", without_cache=False, run_eager=True, prefetch=64, workers=64)


    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/prefetch/dataset/2", without_cache=False, run_eager=False, run_dataset=True, prefetch=1, workers=2)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/prefetch/dataset/4", without_cache=False, run_eager=False, run_dataset=True, prefetch=1, workers=4)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/prefetch/dataset/8", without_cache=False, run_eager=False, run_dataset=True, prefetch=1, workers=8)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/prefetch/dataset/12", without_cache=False, run_eager=False, run_dataset=True, prefetch=1, workers=12)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/prefetch/dataset/16", without_cache=False, run_eager=False, run_dataset=True, prefetch=1, workers=16)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/prefetch/dataset/20", without_cache=False, run_eager=False, run_dataset=True, prefetch=1, workers=20)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/prefetch/dataset/24", without_cache=False, run_eager=False, run_dataset=True, prefetch=1, workers=24)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/prefetch/dataset/28", without_cache=False, run_eager=False, run_dataset=True, prefetch=1, workers=28)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/prefetch/dataset/32", without_cache=False, run_eager=False, run_dataset=True, prefetch=1, workers=32)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/prefetch/dataset/40", without_cache=False, run_eager=False, run_dataset=True, prefetch=1, workers=40)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/prefetch/dataset/48", without_cache=False, run_eager=False, run_dataset=True, prefetch=1, workers=48)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/prefetch/dataset/56", without_cache=False, run_eager=False, run_dataset=True, prefetch=1, workers=56)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/prefetch/dataset/64", without_cache=False, run_eager=False, run_dataset=True, prefetch=1, workers=64)

def test_workers(test_path, file_dir=None):
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/2", without_cache=False, run_eager=True, workers=2)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/4", without_cache=False, run_eager=True, workers=4)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/8", without_cache=False, run_eager=True, workers=8)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/12", without_cache=False, run_eager=True, workers=12)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/16", without_cache=False, run_eager=True, workers=16)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/20", without_cache=False, run_eager=True, workers=20)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/24", without_cache=False, run_eager=True, workers=24)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/28", without_cache=False, run_eager=True, workers=28)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/32", without_cache=False, run_eager=True, workers=32)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/36", without_cache=False, run_eager=True, workers=36)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/40", without_cache=False, run_eager=True, workers=40)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/44", without_cache=False, run_eager=True, workers=44)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/48", without_cache=False, run_eager=True, workers=48)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/52", without_cache=False, run_eager=True, workers=52)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/56", without_cache=False, run_eager=True, workers=56)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/60", without_cache=False, run_eager=True, workers=60)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/workers_eager/64", without_cache=False, run_eager=True, workers=64)

    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/2", without_cache=False, run_eager=False, run_dataset=True, workers=2)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/4", without_cache=False, run_eager=False, run_dataset=True, workers=4)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/8", without_cache=False, run_eager=False, run_dataset=True, workers=8)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/12", without_cache=False, run_eager=False, run_dataset=True, workers=12)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/16", without_cache=False, run_eager=False, run_dataset=True, workers=16)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/20", without_cache=False, run_eager=False, run_dataset=True, workers=20)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/24", without_cache=False, run_eager=False, run_dataset=True, workers=24)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/28", without_cache=False, run_eager=False, run_dataset=True, workers=28)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/32", without_cache=False, run_eager=False, run_dataset=True, workers=32)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/36", without_cache=False, run_eager=False, run_dataset=True, workers=36)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/40", without_cache=False, run_eager=False, run_dataset=True, workers=40)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/44", without_cache=False, run_eager=False, run_dataset=True, workers=44)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/48", without_cache=False, run_eager=False, run_dataset=True, workers=48)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/52", without_cache=False, run_eager=False, run_dataset=True, workers=52)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/56", without_cache=False, run_eager=False, run_dataset=True, workers=56)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/60", without_cache=False, run_eager=False, run_dataset=True, workers=60)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/workers_pytorch/64", without_cache=False, run_eager=False, run_dataset=True, workers=64)

def test_chunk_size(test_path):
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/1", without_cache=False, run_eager=True, chunk_mult=1)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/2", without_cache=False, run_eager=True, chunk_mult=2)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/3", without_cache=False, run_eager=True, chunk_mult=3)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/4", without_cache=False, run_eager=True, chunk_mult=4)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/5", without_cache=False, run_eager=True, chunk_mult=5)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/6", without_cache=False, run_eager=True, chunk_mult=6)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/7", without_cache=False, run_eager=True, chunk_mult=7)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/8", without_cache=False, run_eager=True, chunk_mult=8)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/12", without_cache=False, run_eager=True, chunk_mult=12)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/16", without_cache=False, run_eager=True, chunk_mult=16)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/20", without_cache=False, run_eager=True, chunk_mult=20)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/24", without_cache=False, run_eager=True, chunk_mult=24)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/28", without_cache=False, run_eager=True, chunk_mult=28)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/32", without_cache=False, run_eager=True, chunk_mult=32)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/36", without_cache=False, run_eager=True, chunk_mult=36)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/40", without_cache=False, run_eager=True, chunk_mult=40)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/44", without_cache=False, run_eager=True, chunk_mult=44)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/48", without_cache=False, run_eager=True, chunk_mult=48)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/52", without_cache=False, run_eager=True, chunk_mult=52)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/56", without_cache=False, run_eager=True, chunk_mult=56)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/60", without_cache=False, run_eager=True, chunk_mult=60)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/chunk_size/64", without_cache=False, run_eager=True, chunk_mult=64)

def test_svs(test_path):
    run_eager_iterator_performance_testing_on_directory(directory="./test_files/svs", file_extensions=[".svs"], output_file="./performance_testing.json")


def test_batch_size(test_path, file_dir):
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/batch_size/eager/16", without_cache=False, run_eager=True, batch=16)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/batch_size/eager/32", without_cache=False, run_eager=True, batch=32)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/batch_size/eager/64", without_cache=False, run_eager=True, batch=64)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/batch_size/eager/128", without_cache=False, run_eager=True, batch=128)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/batch_size/eager/256", without_cache=False, run_eager=True, batch=256)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/batch_size/eager/512", without_cache=False, run_eager=True, batch=512)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/batch_size/eager/756", without_cache=False, run_eager=True, batch=756)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/batch_size/eager/1024", without_cache=False, run_eager=True, batch=1024)

    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/batch_size/dataset/16", without_cache=False, run_dataset=True, run_eager=False, batch=16)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/batch_size/dataset/32", without_cache=False, run_dataset=True, run_eager=False, batch=32)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/batch_size/dataset/64", without_cache=False, run_dataset=True, run_eager=False, batch=64)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/batch_size/dataset/128", without_cache=False, run_dataset=True, run_eager=False, batch=128)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/batch_size/dataset/256", without_cache=False, run_dataset=True, run_eager=False, batch=256)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/batch_size/dataset/512", without_cache=False, run_dataset=True, run_eager=False, batch=512)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/batch_size/dataset/1024", without_cache=False, run_dataset=True, run_eager=False, batch=756)
    run_reproducible_performance_evaluation(test_path, file_dir=file_dir, n_runs=5, output_dir="/scr/arosado/performance/batch_size/dataset/1024", without_cache=False, run_dataset=True, run_eager=False, batch=1024)


def test_svs_default(test_path):
    run_reproducible_performance_evaluation(test_path, n_runs=10, output_dir="/scr/arosado/performance/default", without_cache=True)


def test_tile_overlap(test_path):
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/eager/10", without_cache=False, run_eager=True, tile_overlap={'x': 10, 'y': 10})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/eager/25", without_cache=False, run_eager=True, tile_overlap={'x': 25, 'y': 25})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/eager/50", without_cache=False, run_eager=True, tile_overlap={'x': 50, 'y': 50})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/eager/75", without_cache=False, run_eager=True, tile_overlap={'x': 75, 'y': 75})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/eager/100", without_cache=False, run_eager=True, tile_overlap={'x': 100, 'y': 100})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/eager/125", without_cache=False, run_eager=True, tile_overlap={'x': 125, 'y': 125})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/eager/150", without_cache=False, run_eager=True, tile_overlap={'x': 150, 'y': 150})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/eager/175", without_cache=False, run_eager=True, tile_overlap={'x': 175, 'y': 175})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/eager/200", without_cache=False, run_eager=True, tile_overlap={'x': 200, 'y': 200})

    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/non_eager/10", without_cache=False, run_eager=False, run_non_eager=True, tile_overlap={'x': 10, 'y': 10})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/non_eager/25", without_cache=False, run_eager=False, run_non_eager=True, tile_overlap={'x': 25, 'y': 25})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/non_eager/50", without_cache=False, run_eager=False, run_non_eager=True, tile_overlap={'x': 50, 'y': 50})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/non_eager/75", without_cache=False, run_eager=False, run_non_eager=True, tile_overlap={'x': 75, 'y': 75})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/non_eager/100", without_cache=False, run_eager=False, run_non_eager=True, tile_overlap={'x': 100, 'y': 100})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/non_eager/125", without_cache=False, run_eager=False, run_non_eager=True, tile_overlap={'x': 125, 'y': 125})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/non_eager/150", without_cache=False, run_eager=False, run_non_eager=True, tile_overlap={'x': 150, 'y': 150})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/non_eager/175", without_cache=False, run_eager=False, run_non_eager=True, tile_overlap={'x': 175, 'y': 175})
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/tile_overlap/non_eager/200", without_cache=False, run_eager=False, run_non_eager=True, tile_overlap={'x': 200, 'y': 200})


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

def test_svs_dataset_read_performance(test_path, file_dir):
    # run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/dataset_read", without_cache=False, run_dataset=True, performance_type='read', batch=64)
    # run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/dataset_read_wsi_archive", without_cache=False, run_dataset=True, performance_type='read', batch=64)
    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/dataset_read_scratchy", without_cache=False, run_dataset=True, performance_type='read', batch=64)

def test_svs_dataset_inference_performance(test_path, file_dir):
    # transform = v2.Compose(
    #     [
    #         v2.ToImage(),
    #         v2.ToDtype(torch.float32, scale=True),
    #         v2.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    #     ]
    # )

    # run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/dataset_sobel_inference", without_cache=False, run_dataset=True, performance_type='inference_sobel', batch=64, transform=transform)
    # run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/dataset_efficientnetb0_inference", without_cache=False, run_dataset=True, performance_type='inference_efficientnetb0', batch=64, transform=transform)

    transform = v2.Compose(
        [
            v2.ToImage(),
            v2.Resize(size=(224, 224)),
            v2.ToDtype(torch.float32, scale=True),
            v2.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )

    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/dataset_uni2_inference", without_cache=False, run_dataset=True, performance_type='inference_uni2', batch=64, transform=transform)

def test_svs_with_tiff_source(test_path):
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/with_tiff_source", without_cache=True, run_eager=True, with_tiff_source=True)

def test_svs_with_efficientnet(test_path):
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/with_efficientnet", without_cache=False, run_eager=True, performance_type='inference_efficientnetb0')

def test_albumentations_transform(test_path):
    transform = A.Compose([
        A.ToFloat(),
        A.Resize(224, 224),
        A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/with_albumentations_transform/non_eager", without_cache=False, run_eager=False, run_non_eager=True, performance_type='albumentations_transform', transform=transform)


def test_transform(test_path, file_dir):
    albumentations_transform = A.Compose([
        A.ToFloat(),
        A.Resize(224, 224),
        A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    pytorch_transform = v2.Compose(
        [
            v2.ToImage(),
            v2.Resize(size=(224, 224)),
            v2.ToDtype(torch.float32, scale=True),
            v2.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )

    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/transform/dataset/albumentations", without_cache=False, run_eager=False, run_non_eager=False, run_dataset=True, performance_type='albumentations_transform', transform=albumentations_transform)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/transform/non_eager/albumentations", without_cache=False, run_eager=False, run_non_eager=True, performance_type='albumentations_transform', transform=albumentations_transform)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/transform/eager/albumentations", without_cache=False, run_eager=True, run_non_eager=False, performance_type='albumentations_transform', transform=albumentations_transform)
    

    run_reproducible_performance_evaluation(test_path, n_runs=5, file_dir=file_dir, output_dir="/scr/arosado/performance/transform/dataset/pytorch", without_cache=False, run_eager=False, run_non_eager=False, run_dataset=True, performance_type='pytorch_transform', transform=pytorch_transform)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/transform/non_eager/pytorch", without_cache=False, run_eager=False, run_non_eager=True, performance_type='pytorch_transform', transform=pytorch_transform)
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/transform/eager/pytorch", without_cache=False, run_eager=True, run_non_eager=False, performance_type='pytorch_transform', transform=pytorch_transform)
    



def test_svs_with_pytorch_transform(test_path):
    transform = v2.Compose([
        v2.ToImage(),
        v2.RandomResizedCrop(size=(288, 288), antialias=True),
        v2.RandomHorizontalFlip(p=0.5),
        v2.ToDtype(torch.float32, scale=True),
        v2.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    transform = v2.Compose(
        [
            v2.Resize(224),
            v2.ToTensor(),
            v2.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )

    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/with_pytorch_transform", without_cache=False, run_eager=True, run_non_eager=True, performance_type='pytorch_transform', transform=transform)

def test_svs_with_efficientnet(test_path):
    transform = v2.Compose(
        [
            v2.Resize(224),
            v2.ToTensor(),
            v2.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/with_efficientnet", without_cache=False, run_eager=False, performance_type='inference_efficientnetb0', transform=transform)

def test_svs_sobel(test_path):
    transform = v2.Compose(
        [
            v2.Resize(224),
            v2.ToTensor(),
            v2.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/sobel", without_cache=False, run_eager=False, performance_type='inference_sobel', transform=transform)

def test_svs_uni2(test_path):
    transform = v2.Compose(
        [
            v2.ToImage(),
            v2.Resize(size=(224, 224)),
            v2.ToDtype(torch.float32, scale=True),
            v2.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )
    run_reproducible_performance_evaluation(test_path, n_runs=5, output_dir="/scr/arosado/performance/with_uni2", without_cache=False, run_eager=True, performance_type='inference_uni2', compile_model=True, transform=transform)

    transform_rescale = v2.Compose(
        [
            v2.ToImage(),
            v2.ToDtype(torch.float32, scale=True),
            v2.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )

    run_reproducible_performance_evaluation(
        test_path, 
        n_runs=5, 
        output_dir="/scr/arosado/performance/with_uni2_rescale", 
        without_cache=False, 
        run_eager=False, 
        performance_type='inference_uni2', 
        compile_model=True,
        scale={'mm_x': 0.0005, 'mm_y': 0.0005},
        tile_size={'width': 224, 'height': 224},
        transform=transform_rescale
        )

if __name__ == "__main__":
    test_path = '/scr/arosado/tcga/acc/5b9efa00e62914002e94791c_TCGA-OR-A5LL-01Z-00-DX1.08588029-C532-4CDD-B945-251315EFF5C0.svs'
    test_dir = '/scr/arosado/large_image/svs_test_tiles'

    svs_dir = '/scr/arosado/large_image/svs'
    mrxs_dir = '/scr/arosado/large_image/mrxs'
    ndpi_dir = '/scr/arosado/large_image/ndpi'

    transform = v2.Compose(
        [
            v2.ToImage(),
            v2.ToDtype(torch.float32, scale=True),
            v2.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )

    # run_performance_testing_on_directory(svs_dir, file_extensions=[".svs"], output_dir="/scr/arosado/performance/svs", n_runs=5, n_files=10, scale={'mm_x': 0.0005, 'mm_y': 0.0005}, tile_size={'width': 224, 'height': 224}, transform=transform)
    # run_performance_testing_on_directory(mrxs_dir, file_extensions=[".mrxs"], output_dir="/scr/arosado/performance/mrxs", n_runs=5, n_files=10, scale={'mm_x': 0.0005, 'mm_y': 0.0005}, tile_size={'width': 224, 'height': 224}, transform=transform)
    # run_performance_testing_on_directory(ndpi_dir, file_extensions=[".ndpi"], output_dir="/scr/arosado/performance/ndpi", n_runs=5, n_files=10, scale={'mm_x': 0.0005, 'mm_y': 0.0005}, tile_size={'width': 224, 'height': 224}, transform=transform)

    # Test read performance
    # test_read(test_path, test_dir)

    # Test write performance
    # test_write(test_path)

    # Test workers
    # test_workers(test_path, file_dir=test_dir)

    # Test prefetch
    # test_prefetch(test_path, file_dir=test_dir)

    # Test transform performance
    # test_transform(test_path, test_dir)

    # Test high performance read
    # test_read_high_performance(test_path)

    # Test performance with default settings
    # test_svs_default()

    # Test performance with different tile overlaps
    test_tile_overlap(test_path)

    # Test performance with different resolutions
    # test_svs_mag_resolution()

    # Test performance with different batch sizes
    # test_batch_size()

    # Test performance with different chunk sizes
    # test_chunk_size(test_path)

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
    # test_svs_with_pytorch_transform(test_path)

    # Test performance with albumentations transform
    # test_albumentations_transform(test_path)

    # Test performance with sobel
    # test_svs_sobel(test_path)

    # Test performance with efficientnet
    # test_svs_with_efficientnet(test_path)

    # Test performance with uni2
    # test_svs_uni2(test_path)

    # Test dataset read performance
    # test_svs_dataset_read_performance(test_path, file_dir=test_dir)

    # Test dataset inference performance
    # test_svs_dataset_inference_performance(test_path, file_dir=test_dir)

    # Test workers performance
    # test_workers(test_path, file_dir=test_dir)

    pass
