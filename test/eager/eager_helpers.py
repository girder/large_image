import subprocess
import gc
import os
import stat
import time
import functools
import multiprocessing

import h5py
from pathlib import Path
from typing import Callable, Union, Any, Iterable

import pytest
from matplotlib import pyplot as plt
import large_image
import albumentations as A
import numpy as np
import torch
from torch.nn.functional import pad

from large_image.tilesource.eager_utils.eager_shared_array import SharedArray
from large_image.tilesource.eager_utils.eager_image_modifications import rgba2rgb, padding

from test.eager.paper.keras_efficientnet import make_efficientnet_model
from test.eager.paper.huggingface_uni2_model import make_huggingface_uni2_model
from test.eager.paper.pytorch_sobel_model import make_sobel_model

def clear_cache():
    clear_cahce_shell_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'paper', 'clear_cache.sh')
    os.chmod(clear_cahce_shell_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    result = subprocess.run([f'{os.path.dirname(os.path.realpath(__file__))}/paper/clear_cache.sh'])
    if result.returncode != 0:
        raise Exception(f"Failed to clear disk cache: {result.returncode}")
    else:
        print(f"Disk cache cleared")

    # Collect garbage for clearing all LRU cache as well
    gc.collect()

    # All objects collected that have LRU cache
    objects = [i for i in gc.get_objects() 
            if isinstance(i, functools._lru_cache_wrapper)]

    # All objects cleared that have LRU cache
    for object in objects:
        object.cache_clear()

    # Also use cachesClear utility to clear the cache that is managed by large_image special
    # cache wrapper
    from large_image.cache_util import cachesClear
    cachesClear() 

    print(f"LRU cache cleared")

def setup_inference_model(performance_type: str, compile_model: bool = False, cuda_device: str = 'cuda:0'):
    model = None
    # Set sobel model if needed
    if performance_type == 'inference_sobel':
        model = make_sobel_model(compile_model=compile_model, cuda_device=cuda_device)
    elif performance_type == 'inference_efficientnetb0':
        model = make_efficientnet_model(compile_model=compile_model, cuda_device=cuda_device)
    elif performance_type == 'inference_uni2':
        model = make_huggingface_uni2_model(compile_model=compile_model, cuda_device=cuda_device)
    
    return model

def perform_non_eager_inference_with_pytorch_model(model: torch.nn.Module, tile_iterator: Iterable, cuda_device: str = 'cuda:0', **kwargs):
    batch_images = []
    image_shape = None

    if 'batch' in kwargs:
        batch_size = kwargs['batch']
    else:
        batch_size = 64

    def preprocess_image(image, image_shape):
        image = rgba2rgb(image)
        if image.shape[1] != image_shape[1] or image.shape[0] != image_shape[0]:
            pad_width= image_shape[1] - image.shape[1]
            pad_height = image_shape[0] - image.shape[0]
            image = np.pad(image, pad_width=((0, pad_height), (0, pad_width), (0, 0)), mode='constant')            
        transformed_image = kwargs['transform'](image)
        return transformed_image
    
    with torch.inference_mode():
        for tile_dict in tile_iterator:
            image = tile_dict['tile']
            if image_shape is None:
                image_shape = image.shape
            transformed_image = preprocess_image(image, image_shape)
            batch_images.append(transformed_image)
            if len(batch_images) == batch_size:
                batch_images = torch.stack(batch_images)
                batch_images = batch_images.to(cuda_device)
                output = model(batch_images)
                del batch_images
                batch_images = []

        if len(batch_images) > 0:
            batch_images = torch.stack(batch_images)
            batch_images = batch_images.to(cuda_device)
            output = model(batch_images)
            del batch_images
            batch_images = []
    
    return True

def run_non_eager_performance_evaluation(file_path: str, without_cache: bool = False, without_icc: bool = False, with_tiff_source: bool = False, performance_type: str = 'read', compile_model: bool = False, *args, **kwargs):
    performance_data = {}
    add_default_wsi_dimensions(performance_data, file_path)

    if without_cache:
        setup_time, process_time = run_non_eager_read_performance_evaluation(file_path, True, without_icc, with_tiff_source, performance_type, compile_model, **kwargs)
        add_performance_data(performance_data, performance_data['file_dimensions'], 'without_cache', setup_time, process_time)

    setup_time, process_time = run_non_eager_read_performance_evaluation(file_path, False, without_icc, with_tiff_source, performance_type, compile_model, **kwargs)
    add_performance_data(performance_data, performance_data['file_dimensions'], 'with_cache', setup_time, process_time)

    return performance_data

def perform_eager_inference_with_pytorch_model(model: torch.nn.Module, eager_iter: Iterable, cuda_device: str = 'cuda:0'):
    with torch.inference_mode():
        for batch in eager_iter:
            batch_images = batch['tile'].view()
            batch_images = torch.tensor(batch_images)
            batch_images = batch_images.to(cuda_device)
            output = model(batch_images)
            del batch_images

        return True

def run_non_eager_read_performance_evaluation(file_path: str, without_cache: bool = False, without_icc: bool = False, with_tiff_source: bool = False, performance_type: str = 'read', compile_model: bool = False, *args, **kwargs):
    clear_cache()
    
    # Set caching
    if without_cache:
        large_image.config.setConfig('cache_sources', False)
    else:
        large_image.config.setConfig('cache_sources', True)

    # Set ICC correction
    if without_icc:
        large_image.config.setConfig('icc_correction', False)
    else:
        large_image.config.setConfig('icc_correction', True)

    model = setup_inference_model(performance_type, compile_model)

    # Test performance without caching
    start_time = time.time()
    # Set tiff source if needed
    if not with_tiff_source:
        tile_source = large_image.open(file_path, edge='#000000')
    else:
        import large_image_source_tiff
        tile_source = large_image_source_tiff.open(file_path)

    kwargs.update({'format': large_image.constants.TILE_FORMAT_NUMPY})

    tile_iterator = tile_source.tileIterator(**kwargs)
    setup_time = time.time() - start_time
    
    if performance_type == 'read':
        for tile_dict in tile_iterator:
                image = tile_dict['tile']
    elif performance_type == 'transform':
        for tile_dict in tile_iterator:
            image = tile_dict['tile']
    elif performance_type == 'inference':
        for tile_dict in tile_iterator:
            image = tile_dict['tile']
    elif performance_type == 'write':
        for tile_dict in tile_iterator:
            image = tile_dict['tile']
            plt.imsave("./image_{}_{}.png".format(tile_dict['tile_position']['region_x'], tile_dict['tile_position']['region_y']), image)
    elif performance_type == 'pytorch_transform':
        for tile_dict in tile_iterator:
            image = rgba2rgb(tile_dict['tile'])
            transformed_image = kwargs['transform'](image)
    elif performance_type == 'albumentations_transform':
        for tile_dict in tile_iterator:
            image = tile_dict['tile']
            transformed_image = kwargs['transform'](image=image)
    elif performance_type == 'write_multiprocessing':
        images_to_save = []
        
        for tile_dict in tile_iterator:
            images_to_save.append(["./image_{}_{}.png".format(tile_dict['tile_position']['region_x'], tile_dict['tile_position']['region_y']), tile_dict['tile']])
        
        with multiprocessing.Pool(processes=16) as pool:
            pool.starmap(plt.imsave, images_to_save)
            pool.close()
            pool.join()
    elif performance_type == 'inference_sobel':
        model_output = perform_non_eager_inference_with_pytorch_model(model, tile_iterator, **kwargs)
    elif performance_type == 'inference_efficientnetb0':
        model_output = perform_non_eager_inference_with_pytorch_model(model, tile_iterator, **kwargs)
    elif performance_type == 'inference_uni2':
        model_output = perform_non_eager_inference_with_pytorch_model(model, tile_iterator, **kwargs)

    process_time = time.time() - start_time

    # Clean up
    del tile_iterator
    del tile_source
    del model

    return setup_time, process_time

def run_eager_read_performance_evaluation(file_path: str, without_cache: bool = False, without_icc: bool = False, with_tiff_source: bool = False, performance_type: str = 'read', compile_model: bool = False, *args, **kwargs):
    # Clear all caches for fair comparison
    clear_cache()

    model = setup_inference_model(performance_type, compile_model)

    # Set caching
    if without_cache:
        large_image.config.setConfig('cache_sources', False)
    else:
        large_image.config.setConfig('cache_sources', True)

    # Set ICC correction
    if without_icc:
        large_image.config.setConfig('icc_correction', False)
    else:
        large_image.config.setConfig('icc_correction', True)
    
    # Set tiff source if needed
    start_time = time.time()
    if not with_tiff_source:
        if os.path.exists(file_path):
            tile_source = large_image.open(file_path)
        else:
            raise FileNotFoundError(f"File does not exist: {file_path}")
    else:
        import large_image_source_tiff
        tile_source = large_image_source_tiff.open(file_path)
    
    eager_iter = tile_source.eagerIterator(**kwargs)
    setup_time = time.time() - start_time
    
    # Test read only performance
    if performance_type == 'read':
        for batch in eager_iter:
            batch_images = batch['tile'].view()
    # Run write
    elif performance_type == 'write':
        for batch in eager_iter:
            batch_images = batch['tile'].view()

    # Run write with multiprocessing
    elif performance_type == 'write_multiprocessing':
        for batch in eager_iter:
            batch_images = batch['tile'].view()

            images_to_save = []        
            for i in range(batch_images.shape[0]):
                images_to_save.append(["./image_{}_{}.png".format(batch['tile_position']['region_x'][i], batch['tile_position']['region_y'][i]), batch_images[i]])
            
            with multiprocessing.Pool(processes=10) as pool:
                pool.starmap(plt.imsave, images_to_save)
                pool.close()
                pool.join()
    # Run read with albumentations transform
    elif performance_type == 'albumentations_transform':
        for batch in eager_iter:
            batch_images = batch['tile'].view()
            del batch_images
    # Run read with transform
    elif performance_type == 'pytorch_transform':
        for batch in eager_iter:
            batch_images = batch['tile'].view()
            del batch_images
    # Run read with sobel
    elif performance_type == 'inference_sobel':
        perform_eager_inference_with_pytorch_model(model, eager_iter)
    elif performance_type == "inference_efficientnetb0":
        perform_eager_inference_with_pytorch_model(model, eager_iter)
    elif performance_type == 'inference_uni2':
        perform_eager_inference_with_pytorch_model(model, eager_iter)        

    performance_time = time.time() - start_time

    del eager_iter
    del tile_source
    del model

    return setup_time, performance_time


def run_eager_performance_evaluation(file_path: str, without_cache: bool = False, without_icc: bool = False, with_tiff_source: bool = False, performance_type: str = 'read', *args, **kwargs):
    performance_data = {}
    add_default_wsi_dimensions(performance_data, file_path)

    # Test performance with default resolution without caching
    if without_cache:
        setup_time, process_time = run_eager_read_performance_evaluation(file_path, True, without_icc, with_tiff_source, performance_type, **kwargs)
        add_performance_data(performance_data, performance_data['file_dimensions'], 'without_cache', setup_time, process_time)

    # Test read only performance with cache
    setup_time, process_time = run_eager_read_performance_evaluation(file_path, False, without_icc, with_tiff_source, performance_type, **kwargs)
    add_performance_data(performance_data, performance_data['file_dimensions'], 'with_cache', setup_time, process_time)

    return performance_data


def add_default_wsi_dimensions(performance_data: dict, file_path: str):
    # Get the size of the image
    source = large_image.open(file_path)
    target_dimensions = {}
    target_dimensions['x'] = source.getMetadata()['sizeX']
    target_dimensions['y'] = source.getMetadata()['sizeY']
    target_dimensions['tile_width'] = source.getMetadata()['tileWidth']
    target_dimensions['tile_height'] = source.getMetadata()['tileHeight']
    target_dimensions['mm_x'] = source.getMetadata()['mm_x']
    target_dimensions['mm_y'] = source.getMetadata()['mm_y']
    target_dimensions['magnification'] = source.getMetadata()['magnification']

    performance_data['file_dimensions'] = target_dimensions.copy()

    del source

def aggregate_runs(runs: list[dict], output_file_path: str):
    if len(runs) == 0:
        return
    
    file_dir = os.path.dirname(output_file_path)
    os.makedirs(file_dir, exist_ok=True)

    with h5py.File(output_file_path, 'w') as f:
        setup_times_with_cache = []
        setup_times_without_cache = []
        process_times_with_cache = []
        process_times_without_cache = []

        # aggregate runs
        for run in runs:
            if 'with_cache' in run:
                setup_times_with_cache.append(run['with_cache']['setup_time'])
                process_times_with_cache.append(run['with_cache']['process_time'])
            if 'without_cache' in run:
                setup_times_without_cache.append(run['without_cache']['setup_time'])
                process_times_without_cache.append(run['without_cache']['process_time'])

        if len(setup_times_with_cache) > 0:
            setup_times_with_cache = np.array(setup_times_with_cache)
            f.create_dataset('setup_times_with_cache', data=setup_times_with_cache)
        if len(process_times_with_cache) > 0:
            process_times_with_cache = np.array(process_times_with_cache)
            f.create_dataset('process_times_with_cache', data=process_times_with_cache)
        if len(setup_times_without_cache) > 0:
            setup_times_without_cache = np.array(setup_times_without_cache)
            f.create_dataset('setup_times_without_cache', data=setup_times_without_cache)
        if len(process_times_without_cache) > 0:
            process_times_without_cache = np.array(process_times_without_cache)
            f.create_dataset('process_times_without_cache', data=process_times_without_cache)

    return setup_times_with_cache, process_times_with_cache, setup_times_without_cache, process_times_without_cache


def add_performance_data(performance_data: dict, target_dimensions: dict, performance_type: str, setup_time: float, process_time: float):
    performance_entry = {}
    performance_entry['target_dimensions'] = target_dimensions
    performance_entry['setup_time'] = setup_time
    performance_entry['process_time'] = process_time

    performance_data[performance_type] = performance_entry

def run_reproducible_performance_evaluation(file_path: str, n_runs: int = 3, output_dir: str = "./performance", without_cache: bool = False, only_eager: bool = False, without_icc: bool = False, with_tiff_source: bool = False, performance_type: str = 'read', compile_model: bool = False, **kwargs):
    print("Running reproducible performance evaluation with output directory: ", output_dir)
    eager_runs = []
    non_eager_runs = []

    eager_output_filename = "eager_performance_evaluation.h5"
    eager_output_file_path = os.path.join(output_dir, eager_output_filename)

    non_eager_output_filename = "non_eager_performance_evaluation.h5"
    non_eager_output_file_path = os.path.join(output_dir, non_eager_output_filename)
    os.makedirs(output_dir, exist_ok=True)
    
    for i in range(n_runs):
        print(f"Running eager performance evaluation {i+1} of {n_runs} with kwargs: {kwargs}")
        performance_data = run_eager_performance_evaluation(file_path, without_cache, without_icc, with_tiff_source, performance_type, compile_model, **kwargs)
        eager_runs.append(performance_data)

    if not only_eager:
        for i in range(n_runs):
            print(f"Running non-eager performance evaluation {i+1} of {n_runs} with kwargs: {kwargs}")
            performance_data = run_non_eager_performance_evaluation(file_path, without_cache, without_icc, with_tiff_source, performance_type, compile_model, **kwargs)
            non_eager_runs.append(performance_data)
    
    eager_runs = aggregate_runs(eager_runs, eager_output_file_path)
    non_eager_runs = aggregate_runs(non_eager_runs, non_eager_output_file_path)
    
    return eager_runs, non_eager_runs


def run_eager_iterator_performance_testing_on_directory(directory: str, file_extensions: list[str] = ['.tif', '.svs', '.mrxs'], output_file: str = "./performance_testing.json"):
    # Make directory for output file if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    
    # Search through the directory for files with the given extensions
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(tuple(file_extensions)):
                # Get information about the file
                file_ext = os.path.splitext(file)[1]
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)

                performance_data = run_eager_performance_evaluation(file_path)
                
                pass
                

def run_batch_size(tile_source: large_image.tilesource, batch_size: int=64):
    iterator = tile_source.eagerIterator(output_mode='tiles', batch=batch_size)
    for batch in iterator:
        batch_images = batch[0].view()
        batch_image = batch_images[0]
        batch_image_copy = batch_image[:]
        assert batch_images.shape[0] == batch_size
        assert len(batch_images.shape) == 4
        assert np.all(batch_image == batch_image_copy)
        break

def build_numpy_shared_array(array_shape: tuple[int, int, int] = (256, 256, 3), dtype: np.dtype = np.uint8, is_torch: bool = False):
    shared_array = SharedArray(array_shape, dtype, is_torch)
    return shared_array

def build_torch_shared_array(array_shape: tuple[int, int, int] = (256, 256, 3), dtype: torch.dtype = torch.uint8, is_torch: bool = True):
    shared_array = SharedArray(array_shape, dtype, is_torch)
    return shared_array

def run_eager_iterator_with_albumentations_transform(tile_source: large_image.tilesource, transform: A.Compose):
    try:
        start_time = time.time()
        iterator = tile_source.eagerIterator(output_mode='tiles', transform=transform)
        # Count output images provided by the iterator
        output_image_count = iterator.get_output_image_count()
        # Count tiles provided by the iterator based on the slide dimensions if a subset not selected
        tile_image_count = iterator.slide_dimensions['tile_target_range_x'] * iterator.slide_dimensions['tile_target_range_y']

        # Count tiles provided by the iterator
        count = 0
        for batch in iterator:
            batch_images = batch['tile']
            count += batch_images.shape[0]

        del iterator
        
        end_time = time.time()
        print(f"Time taken: {end_time - start_time} seconds")

        return output_image_count, tile_image_count, count
    
    except Exception as e:
        raise e

def run_eager_iterator_numpy_dtype(test_file: Any, dtype: np.dtype):
    source, iterator = build_eager_iterator(test_file, dtype=dtype)
    for batch in iterator:
        batch_images = batch[0].view()
        assert batch_images.dtype == dtype, f"Expected {dtype}, got {batch_images.dtype}"

def build_eager_iterator(test_file: Any, scale_mode: str = 'mag', target_scale: int = 20, tile_size: tuple[int, int] = (224, 224), overlap: int = 0, chunk_mult: int = 4, mask: str = None, output_mode: str = 'tiles', transform: Callable = None, dtype: np.dtype = np.uint8, batch: int = 64):
    source = large_image.open(test_file)
    iterator = source.eagerIterator(scale_mode=scale_mode, target_scale=target_scale, tile_size=tile_size, overlap=overlap, chunk_mult=chunk_mult, mask=mask, output_mode=output_mode, transform=transform, batch=batch, dtype=dtype)
    return source, iterator

@pytest.fixture(scope='module')
def test_eager_iterator_image(test_file: Any, output_dir_path: Union[str, Path], target_scale: int = 5, tile_size: tuple[int, int] = (224, 224)):
    source, iterator = build_eager_iterator(test_file, target_scale=target_scale, tile_size=tile_size)
    
    thumbnail, _ = source.getThumbnail(size=(1024, 1024), format='numpy')
    thumbnail_output_path = os.path.join(output_dir_path, 'thumbnail.png')
    plt.imsave(thumbnail_output_path, thumbnail)
    
    test_large_image = np.zeros((iterator.slide_dimensions['tile_target_range_y']*tile_size[1], iterator.slide_dimensions['tile_target_range_x']*tile_size[0], 3), dtype=np.uint8)
    for batch in iterator:
        batch_images = batch[0].view()
        batch_read_kwargs = batch[1]
        for i in range(batch_images.shape[0]):
            x = int(batch_read_kwargs['tile_position']['region_x'][i].item())
            y = int(batch_read_kwargs['tile_position']['region_y'][i].item())
            image = batch_images[i]
            test_large_image[y*tile_size[1]:(y+1)*tile_size[1], x*tile_size[0]:(x+1)*tile_size[0], :] = image[:, :, :]

    large_image_output_path = os.path.join(output_dir_path, 'large_image.png')
    plt.imsave(large_image_output_path, test_large_image)


def run_eager_iterator_with_pytorch_transform(tile_source: large_image.tilesource, transform: Callable):
    start_time = time.time()
    iterator = tile_source.eagerIterator(output_mode='tiles', transform=transform)

    # Count output images provided by the iterator
    output_image_count = iterator.get_output_image_count()
    # Count tiles provided by the iterator based on the slide dimensions if a subset not selected
    tile_image_count = iterator.slide_dimensions['tile_target_range_x'] * iterator.slide_dimensions['tile_target_range_y']

    # Count tiles provided by the iterator
    count = 0
    for batch in iterator:
        batch_images = batch[0].view()
        count += batch_images.shape[0]

    del iterator
    
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")

    return output_image_count, tile_image_count, count