import functools
import gc
import multiprocessing
import os
import stat
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Union

import albumentations as A
import cv2
import h5py
import numpy as np
import pytest
import torch
from matplotlib import pyplot as plt
from torchvision.io import ImageReadMode

import large_image
from large_image.tilesource.eager_utils.eager_image_modifications import rgba2rgb
from large_image.tilesource.eager_utils.eager_shared_array import SharedArray
from large_image.tilesource.eager_utils.eager_wsi_operations import calculate_slide_dimensions

INFERENCE_PERFORMANCE_TYPES = {
    'inference_sobel',
    'inference_efficientnetb0',
    'inference_uni2',
    'inference_uni',
}

NON_EAGER_READ_PERFORMANCE_TYPES = {'read', 'transform', 'inference'}
TRANSFORM_PERFORMANCE_TYPES = {'pytorch_transform', 'albumentations_transform'}
DATASET_UNIMPLEMENTED_PERFORMANCE_TYPES = {
    'write': 'Write task is not implemented for dataset tasks',
    'write_multiprocessing': 'Write multiprocessing task is not implemented for dataset tasks',
    'write_transform': 'Write transform task is not implemented for dataset tasks',
}

EAGER_TEST_REGION = {
    'left': 0,
    'top': 0,
    'width': 1000,
    'height': 1000,
    'units': 'base_pixels',
}


def matplotlib_save_image(image_path: str, image: np.ndarray):
    start_save_time = time.time()
    plt.imsave(image_path, image)
    end_save_time = time.time()
    return end_save_time - start_save_time


def make_pytorch_dataset(input_image_dir: str, transform: Optional[Callable] = None):
    from torch.utils.data import Dataset
    from torchvision.io import read_image

    class ImageDataset(Dataset):
        def __init__(self, image_dir: str, transform: Optional[Callable] = None):
            self.image_dir = image_dir
            self.image_paths = [
                os.path.join(image_dir, f) for f in os.listdir(image_dir) if f.endswith('.png')
            ]
            self.transform = transform

        def __len__(self):
            return len(self.image_paths)

        def __getitem__(self, idx):
            image_path = self.image_paths[idx]
            image = read_image(image_path, mode=ImageReadMode.RGB)
            if self.transform is not None:
                if isinstance(self.transform, A.Compose):
                    image = image.numpy()
                    image = self.transform(image=image)
                elif isinstance(self.transform, Callable):
                    image = self.transform(image)
            return image

    dataset = ImageDataset(input_image_dir, transform)
    return dataset


def clear_cache():
    clear_cahce_shell_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'paper',
        'clear_cache.sh',
    )
    os.chmod(
        clear_cahce_shell_path,
        stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH,
    )
    result = subprocess.run([f'{os.path.dirname(os.path.realpath(__file__))}/paper/clear_cache.sh'])
    if result.returncode != 0:
        msg = f'Failed to clear disk cache: {result.returncode}'
        raise Exception(msg)
    print('Disk cache cleared')

    gc.collect()

    # All objects collected that have LRU cache
    objects = [i for i in gc.get_objects() if isinstance(i, functools._lru_cache_wrapper)]

    # All objects cleared that have LRU cache
    for object in objects:
        object.cache_clear()

    # Also use cachesClear utility to clear the cache that is managed by large_image special
    # cache wrapper
    from large_image.cache_util import cachesClear

    cachesClear()

    # Clear GPU
    torch.cuda.empty_cache()

    # Collect garbage for clearing all LRU cache as well
    gc.collect()

    print('LRU cache cleared')


def setup_inference_model(
    performance_type: str,
    compile_model: bool = True,
    cuda_device: str = 'cuda:0',
):
    model = None
    # Set sobel model if needed
    if performance_type == 'inference_sobel':
        from test.eager.paper.pytorch_sobel_model import make_sobel_model

        model = make_sobel_model(compile_model=compile_model, cuda_device=cuda_device)
    elif performance_type == 'inference_efficientnetb0':
        from test.eager.paper.pytorch_efficientnet import make_efficientnet_model

        model = make_efficientnet_model(compile_model=compile_model, cuda_device=cuda_device)
    elif performance_type == 'inference_uni2':
        from test.eager.paper.huggingface_uni2_model import make_huggingface_uni2_model

        model = make_huggingface_uni2_model(compile_model=compile_model, cuda_device=cuda_device)
    elif performance_type == 'inference_uni':
        from test.eager.paper.huggingface_uni2_model import make_huggingface_uni_model

        model = make_huggingface_uni_model(compile_model=compile_model, cuda_device=cuda_device)

    return model


def calculate_batch_retreival_time(
    start_iterator_retreival_time: float,
    end_batch_retreival_time: float,
    end_inference_times: list[float],
):
    if len(end_inference_times) == 0:
        return end_batch_retreival_time - start_iterator_retreival_time
    if len(end_inference_times) > 0:
        last_batch_retreival_time = end_inference_times[-1]
        return end_batch_retreival_time - last_batch_retreival_time


def set_large_image_performance_config(without_cache: bool, without_icc: bool):
    large_image.config.setConfig('cache_sources', not without_cache)
    large_image.config.setConfig('icc_correction', not without_icc)


def open_performance_tile_source(
    file_path: str,
    with_tiff_source: bool = False,
    edge: str | None = None,
    check_exists: bool = False,
):
    if with_tiff_source:
        import large_image_source_tiff

        return large_image_source_tiff.open(file_path)

    if check_exists and not os.path.exists(file_path):
        msg = f'File does not exist: {file_path}'
        raise FileNotFoundError(msg)

    if edge is None:
        return large_image.open(file_path)
    return large_image.open(file_path, edge=edge)


def make_performance_write_directory(performance_type: str, runner_name: str):
    write_directories = {
        ('non_eager', 'write'): '/scr/arosado/performance/write/non_eager/default/images',
        (
            'non_eager',
            'write_multiprocessing',
        ): '/scr/arosado/performance/write/non_eager/multiprocessing/images',
        ('eager', 'write'): '/scr/arosado/performance/write/eager/default/images',
        (
            'eager',
            'write_multiprocessing',
        ): '/scr/arosado/performance/write/eager/multiprocessing/images',
        ('eager', 'write_transform'): '/scr/arosado/performance/write/eager/transform/images',
    }
    write_directory = write_directories.get((runner_name, performance_type))
    if write_directory is not None:
        os.makedirs(write_directory, exist_ok=True)
    return write_directory


def make_tile_write_path(write_directory: str, region_x, region_y):
    return f'{write_directory}/image_{int(region_x)}_{int(region_y)}.png'


def copy_eager_test_region() -> dict[str, Any]:
    return dict(EAGER_TEST_REGION)


def get_output_image_count(source: large_image.tilesource, region: dict[str, Any] | None = None):
    region = region or EAGER_TEST_REGION
    slide_dimensions = calculate_slide_dimensions(source, region)
    return (
        slide_dimensions['tile_target_range_x'] *
        slide_dimensions['tile_target_range_y']
    )


def perform_pytorch_dataset_inference(
    dataloader: torch.utils.data.DataLoader,
    model: torch.nn.Module,
    cuda_device: str = 'cuda:0',
    **kwargs,
):
    inference_times = []
    batch_retreival_times = []

    with torch.inference_mode() and torch.no_grad():
        start_iterator_retreival_time = time.time()
        for batch in dataloader:
            batch_images = batch.to(cuda_device)
            start_inference_time = time.time()
            batch_retreival_times.append(start_inference_time - start_iterator_retreival_time)
            model(batch_images)
            del batch_images
            end_inference_time = time.time()
            inference_times.append(end_inference_time - start_inference_time)

    return batch_retreival_times, inference_times


def perform_non_eager_inference_with_pytorch_model(
    model: torch.nn.Module,
    tile_iterator: Iterable,
    cuda_device: str = 'cuda:0',
    **kwargs,
):
    batch_images = []
    image_shape = None

    if 'batch' in kwargs:
        batch_size = kwargs['batch']
    else:
        batch_size = 64

    def preprocess_image(image, image_shape):
        image = rgba2rgb(image)
        if image.shape[1] != image_shape[1] or image.shape[0] != image_shape[0]:
            pad_width = image_shape[1] - image.shape[1]
            pad_height = image_shape[0] - image.shape[0]
            image = np.pad(
                image,
                pad_width=((0, pad_height), (0, pad_width), (0, 0)),
                mode='constant',
            )
        transformed_image = kwargs['transform'](image)
        return transformed_image

    inference_times = []
    batch_retreival_times = []

    with torch.inference_mode() and torch.no_grad():
        start_iterator_retreival_time = time.time()
        for tile_dict in tile_iterator:
            image = tile_dict['tile']
            if image_shape is None:
                image_shape = image.shape
            transformed_image = preprocess_image(image, image_shape)
            batch_images.append(transformed_image)
            if len(batch_images) == batch_size:
                batch_images = torch.stack(batch_images)
                batch_images = batch_images.to(cuda_device)
                start_inference_time = time.time()
                batch_retreival_times.append(start_inference_time - start_iterator_retreival_time)
                model(batch_images)
                end_inference_time = time.time()
                inference_times.append(end_inference_time - start_inference_time)
                del batch_images
                batch_images = []
                start_iterator_retreival_time = time.time()

        if len(batch_images) > 0:
            batch_images = torch.stack(batch_images)
            batch_images = batch_images.to(cuda_device)
            start_inference_time = time.time()
            batch_retreival_times.append(start_inference_time - start_iterator_retreival_time)
            model(batch_images)
            end_inference_time = time.time()
            inference_times.append(end_inference_time - start_inference_time)
            del batch_images
            batch_images = []

    return batch_retreival_times, inference_times


def run_non_eager_performance_evaluation(
    file_path: str,
    without_cache: bool = False,
    without_icc: bool = False,
    with_tiff_source: bool = False,
    performance_type: str = 'read',
    compile_model: bool = True,
    track_memory: bool = False,
    track_energy: bool = False,
    output_dir: str = './performance',
    n_evaluation: int = 0,
    *args,
    **kwargs,
):
    performance_data = {}
    add_default_wsi_dimensions(performance_data, file_path, **kwargs)

    def run_non_eager_performance():
        if without_cache:
            setup_time, process_time, batch_retreival_times, inference_times, write_times = (
                run_non_eager_task_performance_evaluation(
                    file_path,
                    True,
                    without_icc,
                    with_tiff_source,
                    performance_type,
                    compile_model,
                    track_memory,
                    output_dir,
                    **kwargs,
                )
            )
            add_performance_data(
                performance_data,
                performance_data['file_dimensions'],
                'without_cache',
                setup_time,
                process_time,
                batch_retreival_times,
                inference_times,
                write_times,
            )
        else:
            setup_time, process_time, batch_retreival_times, inference_times, write_times = (
                run_non_eager_task_performance_evaluation(
                    file_path,
                    False,
                    without_icc,
                    with_tiff_source,
                    performance_type,
                    compile_model,
                    track_memory,
                    output_dir,
                    **kwargs,
                )
            )
            add_performance_data(
                performance_data,
                performance_data['file_dimensions'],
                'with_cache',
                setup_time,
                process_time,
                batch_retreival_times,
                inference_times,
                write_times,
            )

    if track_energy:
        from zeus.monitor import ZeusMonitor

        monitor = ZeusMonitor(gpu_indices=[0])
        monitor.begin_window('performance_evaluation')

    if track_memory:
        import memray

        with memray.Tracker(
            os.path.join(output_dir, f'non_eager_{n_evaluation}.bin'),
            follow_fork=True,
            native_traces=True,
        ):
            run_non_eager_performance()
    else:
        run_non_eager_performance()

    if track_energy:
        performance_data = add_energy_data(monitor, performance_data)

    return performance_data


def perform_eager_inference_with_pytorch_model(
    model: torch.nn.Module,
    eager_iter: Iterable,
    cuda_device: str = 'cuda:0',
):
    inference_times = []
    batch_retreival_times = []

    with torch.inference_mode() and torch.no_grad():
        start_iterator_retreival_time = time.time()
        for batch in eager_iter:
            batch_images = batch['tile'].view()
            batch_images = batch_images.to(cuda_device)
            start_inference_time = time.time()
            batch_retreival_times.append(start_inference_time - start_iterator_retreival_time)
            model(batch_images)
            end_inference_time = time.time()
            inference_times.append(end_inference_time - start_inference_time)
            del batch_images
            start_iterator_retreival_time = time.time()

        return batch_retreival_times, inference_times


def run_non_eager_task_performance_evaluation(
    file_path: str,
    without_cache: bool = False,
    without_icc: bool = False,
    with_tiff_source: bool = False,
    performance_type: str = 'read',
    compile_model: bool = True,
    *args,
    **kwargs,
):
    clear_cache()

    batch_retreival_times = []
    write_times = []
    inference_times = []

    set_large_image_performance_config(without_cache, without_icc)
    model = setup_inference_model(performance_type, compile_model)
    write_directory = make_performance_write_directory(performance_type, 'non_eager')

    start_time = time.time()
    tile_source = open_performance_tile_source(file_path, with_tiff_source, edge='#000000')
    kwargs.update({'format': large_image.constants.TILE_FORMAT_NUMPY})

    tile_iterator = tile_source.tileIterator(**kwargs)
    setup_time = time.time() - start_time

    if performance_type == 'regions':
        run_non_eager_region_performance(tile_source, kwargs)
    elif performance_type == 'write':
        run_non_eager_write_performance(
            tile_iterator,
            write_directory,
            batch_retreival_times,
            write_times,
        )
    elif performance_type == 'write_multiprocessing':
        write_times = run_non_eager_multiprocessing_write_performance(
            tile_iterator,
            write_directory,
            batch_retreival_times,
        )
    elif performance_type == 'write_transform':
        msg = 'Write transform task is not implemented for non eager tasks'
        raise NotImplementedError(msg)
    elif performance_type in INFERENCE_PERFORMANCE_TYPES:
        batch_retreival_times, inference_times = perform_non_eager_inference_with_pytorch_model(
            model,
            tile_iterator,
            **kwargs,
        )
    elif performance_type in NON_EAGER_READ_PERFORMANCE_TYPES | TRANSFORM_PERFORMANCE_TYPES:
        run_non_eager_tile_read_performance(
            tile_iterator,
            batch_retreival_times,
            get_non_eager_transform(performance_type, kwargs),
        )

    process_time = time.time() - start_time

    del tile_iterator
    del tile_source
    del model

    return setup_time, process_time, batch_retreival_times, inference_times, write_times


def run_non_eager_tile_read_performance(
    tile_iterator: Iterable,
    batch_retreival_times: list[float],
    transform: Callable | None = None,
):
    start_iterator_retreival_time = time.time()
    for tile_dict in tile_iterator:
        image = tile_dict['tile']
        if transform is not None:
            transform(image)
        end_batch_retreival_time = time.time()
        batch_retreival_times.append(
            calculate_batch_retreival_time(
                start_iterator_retreival_time,
                end_batch_retreival_time,
                batch_retreival_times,
            ),
        )


def run_non_eager_region_performance(tile_source, kwargs: dict[str, Any]):
    if 'regions' not in kwargs:
        msg = 'regions must be provided for regions performance type'
        raise ValueError(msg)

    for region in kwargs['regions']:
        tile_source.getRegion(
            region={
                'left': int(region[1].item()),
                'top': int(region[0].item()),
                'width': int(region[3] - region[1]),
                'height': int(region[2] - region[0]),
            },
            format=large_image.constants.TILE_FORMAT_NUMPY,
        )


def run_non_eager_write_performance(
    tile_iterator: Iterable,
    write_directory: str,
    batch_retreival_times: list[float],
    write_times: list[float],
):
    start_iterator_retreival_time = time.time()
    for tile_dict in tile_iterator:
        image = tile_dict['tile']
        end_batch_retreival_time = time.time()
        plt.imsave(
            make_tile_write_path(
                write_directory,
                tile_dict['tile_position']['region_x'],
                tile_dict['tile_position']['region_y'],
            ),
            image,
        )
        write_times.append(time.time() - end_batch_retreival_time)
        batch_retreival_times.append(
            calculate_batch_retreival_time(
                start_iterator_retreival_time,
                end_batch_retreival_time,
                batch_retreival_times,
            ),
        )


def run_non_eager_multiprocessing_write_performance(
    tile_iterator: Iterable,
    write_directory: str,
    batch_retreival_times: list[float],
):
    images_to_save = []
    start_batch_retreival_time = time.time()
    for tile_dict in tile_iterator:
        images_to_save.append(
            [
                make_tile_write_path(
                    write_directory,
                    tile_dict['tile_position']['region_x'],
                    tile_dict['tile_position']['region_y'],
                ),
                tile_dict['tile'],
            ],
        )
        end_batch_retreival_time = time.time()
        batch_retreival_times.append(end_batch_retreival_time - start_batch_retreival_time)
        start_batch_retreival_time = end_batch_retreival_time

    with multiprocessing.Pool(processes=16) as pool:
        write_times = pool.starmap(matplotlib_save_image, images_to_save)
        pool.close()
        pool.join()
    return write_times


def get_non_eager_transform(performance_type: str, kwargs: dict[str, Any]):
    if performance_type == 'pytorch_transform':
        return lambda image: kwargs['transform'](rgba2rgb(image))
    if performance_type == 'albumentations_transform':
        return lambda image: kwargs['transform'](image=image)
    return None


def generate_random_tile_indexes(
    source,
    size: int,
    scale: dict | None = None,
    tile_size: dict | None = None,
    tile_overlap: dict | None = None,
    region: dict | None = None,
    seed: int | None = None,
) -> np.ndarray:
    """
    Generate random, unique tile indexes for eagerIterator's ``tiles`` parameter.

    Returns an array shaped ``(size, 2)`` in ``[tile_y, tile_x]`` order.
    """
    if size <= 0:
        msg = 'size must be > 0'
        raise ValueError(msg)

    # Probe iterator to compute valid tile index ranges for the selected options.
    probe = source.eagerIterator(
        scale=scale,
        tile_size=tile_size,
        tile_overlap=tile_overlap,
        region=region,
        batch=1,
        prefetch=1,
        workers=2,
    )
    try:
        tile_range_y = int(probe.slide_dimensions['tile_target_range_y'])
        tile_range_x = int(probe.slide_dimensions['tile_target_range_x'])
    finally:
        probe.cleanup()
        del probe

    total_tiles = tile_range_y * tile_range_x
    if size > total_tiles:
        msg = (
            f'Requested {size} tiles, but only {total_tiles} are available '
            f'for this source/scale configuration.'
        )
        raise ValueError(
            msg,
        )

    rng = np.random.default_rng(seed)
    linear_idx = rng.choice(total_tiles, size=size, replace=False)
    tile_y = linear_idx // tile_range_x
    tile_x = linear_idx % tile_range_x

    return np.column_stack((tile_y, tile_x)).astype(np.int64)


def run_dataset_read_performance(dataloader: Iterable, batch_retreival_times: list[float]):
    start_batch_retreival_time = time.time()
    for _batch in dataloader:
        batch_retreival_times.append(time.time() - start_batch_retreival_time)
        if len(batch_retreival_times) != 1:
            start_batch_retreival_time = time.time()


def run_dataset_task_performance_evaluation(
    file_path: str,
    file_dir: str,
    performance_type: str = 'read',
    compile_model: bool = True,
    *args,
    **kwargs,
):
    clear_cache()

    batch_retreival_times = []
    write_times = []
    inference_times = []

    model = setup_inference_model(performance_type, compile_model)

    from torch.utils.data import DataLoader

    start_time = time.time()

    dataset = make_pytorch_dataset(file_dir, transform=kwargs.get('transform'))
    dataloader = DataLoader(
        dataset,
        batch_size=kwargs.get('batch', 64),
        shuffle=False,
        num_workers=kwargs.get('workers', 16),
        prefetch_factor=kwargs.get('prefetch', 16),
    )
    setup_time = time.time() - start_time

    if performance_type == 'read':
        run_dataset_read_performance(dataloader, batch_retreival_times)
    elif performance_type in DATASET_UNIMPLEMENTED_PERFORMANCE_TYPES:
        raise NotImplementedError(DATASET_UNIMPLEMENTED_PERFORMANCE_TYPES[performance_type])
    elif performance_type in TRANSFORM_PERFORMANCE_TYPES:
        start_batch_retreival_time = time.time()
        for _batch in dataloader:
            end_batch_retreival_time = time.time()
            batch_retreival_times.append(end_batch_retreival_time - start_batch_retreival_time)
    elif performance_type in INFERENCE_PERFORMANCE_TYPES:
        batch_retreival_times, inference_times = perform_pytorch_dataset_inference(
            dataloader,
            model,
            **kwargs,
        )

    performance_time = time.time() - start_time

    return setup_time, performance_time, batch_retreival_times, inference_times, write_times


def run_eager_batch_read_performance(eager_iter: Iterable, batch_retreival_times: list[float]):
    start_batch_retreival_time = time.time()
    for batch in eager_iter:
        batch['tile'].view()
        end_batch_retreival_time = time.time()
        batch_retreival_times.append(end_batch_retreival_time - start_batch_retreival_time)
        start_batch_retreival_time = end_batch_retreival_time


def consume_eager_batches(eager_iter: Iterable):
    for batch in eager_iter:
        batch_images = batch['tile'].view()
        del batch_images


def run_eager_write_performance(
    eager_iter: Iterable,
    write_directory: str,
    batch_retreival_times: list[float],
    write_times: list[float],
):
    start_batch_retreival_time = time.time()
    for batch in eager_iter:
        batch_images = batch['tile'].view()
        end_batch_retreival_time = time.time()
        batch_retreival_times.append(end_batch_retreival_time - start_batch_retreival_time)
        start_batch_retreival_time = end_batch_retreival_time

        for i in range(batch_images.shape[0]):
            plt.imsave(
                make_tile_write_path(
                    write_directory,
                    batch['tile_position']['region_x'][i],
                    batch['tile_position']['region_y'][i],
                ),
                batch_images[i],
            )
            write_times.append(time.time() - end_batch_retreival_time)


def run_eager_multiprocessing_write_performance(
    eager_iter: Iterable,
    write_directory: str,
    batch_retreival_times: list[float],
):
    images_to_save = []
    start_batch_retreival_time = time.time()
    for batch in eager_iter:
        batch_images = batch['tile'].view()
        end_batch_retreival_time = time.time()
        batch_retreival_times.append(end_batch_retreival_time - start_batch_retreival_time)
        start_batch_retreival_time = end_batch_retreival_time

        for i in range(batch_images.shape[0]):
            images_to_save.append(
                [
                    make_tile_write_path(
                        write_directory,
                        batch['tile_position']['region_x'][i].item(),
                        batch['tile_position']['region_y'][i].item(),
                    ),
                    batch_images[i].copy(),
                ],
            )

    with multiprocessing.Pool(processes=16) as pool:
        write_times = pool.starmap(matplotlib_save_image, images_to_save)
        pool.close()
        pool.join()
    return write_times


def run_eager_task_performance_evaluation(
    file_path: str,
    without_cache: bool = False,
    without_icc: bool = False,
    with_tiff_source: bool = False,
    performance_type: str = 'read',
    compile_model: bool = True,
    *args,
    **kwargs,
):
    # Clear all caches for fair comparison
    clear_cache()

    batch_retreival_times = []
    inference_times = []
    write_times = []

    model = setup_inference_model(performance_type, compile_model)
    set_large_image_performance_config(without_cache, without_icc)
    write_directory = make_performance_write_directory(performance_type, 'eager')

    start_time = time.time()
    tile_source = open_performance_tile_source(
        file_path,
        with_tiff_source,
        check_exists=True,
    )

    eager_iter = tile_source.eagerIterator(**kwargs)
    setup_time = time.time() - start_time

    if performance_type in {'read', 'write_transform'}:
        run_eager_batch_read_performance(eager_iter, batch_retreival_times)
    elif performance_type == 'write':
        run_eager_write_performance(
            eager_iter,
            write_directory,
            batch_retreival_times,
            write_times,
        )
    elif performance_type == 'write_multiprocessing':
        write_times = run_eager_multiprocessing_write_performance(
            eager_iter,
            write_directory,
            batch_retreival_times,
        )
    elif performance_type in TRANSFORM_PERFORMANCE_TYPES:
        consume_eager_batches(eager_iter)
    elif performance_type in INFERENCE_PERFORMANCE_TYPES:
        batch_retreival_times, inference_times = perform_eager_inference_with_pytorch_model(
            model,
            eager_iter,
        )

    performance_time = time.time() - start_time

    del eager_iter
    del tile_source
    del model

    return setup_time, performance_time, batch_retreival_times, inference_times, write_times


def add_energy_data(monitor: Any, performance_data: dict):
    energy_data = monitor.end_window('performance_evaluation')
    performance_data['energy_data'] = {
        'cpu_energy': energy_data.cpu_energy,
        'gpu_energy': energy_data.gpu_energy,
        'dram_energy': energy_data.dram_energy,
        'time': energy_data.time,
    }

    return performance_data


def run_eager_performance_evaluation(
    file_path: str,
    without_cache: bool = False,
    without_icc: bool = False,
    with_tiff_source: bool = False,
    performance_type: str = 'read',
    compile_model: bool = True,
    track_class_memory: bool = False,
    track_energy: bool = False,
    output_dir: str = './performance',
    n_evaluation: int = 0,
    *args,
    **kwargs,
):
    performance_data = {}
    add_default_wsi_dimensions(performance_data, file_path, **kwargs)

    def run_eager_performance():
        # Test performance with default resolution without caching
        if without_cache:
            setup_time, process_time, batch_retreival_times, inference_times, write_times = (
                run_eager_task_performance_evaluation(
                    file_path,
                    True,
                    without_icc,
                    with_tiff_source,
                    performance_type,
                    compile_model,
                    **kwargs,
                )
            )
            add_performance_data(
                performance_data,
                performance_data['file_dimensions'],
                'without_cache',
                setup_time,
                process_time,
                batch_retreival_times,
                inference_times,
                write_times,
            )
        else:
            # Test read only performance with cache
            setup_time, process_time, batch_retreival_times, inference_times, write_times = (
                run_eager_task_performance_evaluation(
                    file_path,
                    False,
                    without_icc,
                    with_tiff_source,
                    performance_type,
                    compile_model,
                    **kwargs,
                )
            )
            add_performance_data(
                performance_data,
                performance_data['file_dimensions'],
                'with_cache',
                setup_time,
                process_time,
                batch_retreival_times,
                inference_times,
                write_times,
            )

    if track_energy:
        from zeus.monitor import ZeusMonitor

        monitor = ZeusMonitor(gpu_indices=[0])

        monitor.begin_window('performance_evaluation')

    if track_class_memory:
        import memray

        with memray.Tracker(
            os.path.join(output_dir, f'eager_{n_evaluation}.bin'),
            follow_fork=True,
            native_traces=True,
        ):
            run_eager_performance()
    else:
        run_eager_performance()

    if track_energy:
        performance_data = add_energy_data(monitor, performance_data)

    return performance_data


def run_dataset_performance_evaluation(
    file_path: str,
    file_dir: str,
    performance_type: str = 'read',
    compile_model: bool = True,
    track_memory: bool = False,
    track_energy: bool = False,
    output_dir: str = './performance',
    n_evaluation: int = 0,
    *args,
    **kwargs,
):
    performance_data = {}

    def run_dataset_performance():
        add_default_wsi_dimensions(performance_data, file_path, **kwargs)

        # Test performance with default resolution without caching
        setup_time, process_time, batch_retreival_times, inference_times, write_times = (
            run_dataset_task_performance_evaluation(
                file_path,
                file_dir,
                performance_type,
                compile_model,
                track_memory,
                output_dir,
                **kwargs,
            )
        )
        add_performance_data(
            performance_data,
            performance_data['file_dimensions'],
            'pytorch_dataset',
            setup_time,
            process_time,
            batch_retreival_times,
            inference_times,
            write_times,
        )

    if track_energy:
        from zeus.monitor import ZeusMonitor

        monitor = ZeusMonitor(gpu_indices=[0])
        monitor.begin_window('performance_evaluation')

    if track_memory:
        import memray

        memray.dump_all_records()
        with memray.Tracker(
            os.path.join(output_dir, f'dataset_{n_evaluation}.bin'),
            follow_fork=True,
            native_traces=True,
        ):
            run_dataset_performance()
    else:
        run_dataset_performance()

    if track_energy:
        performance_data = add_energy_data(monitor, performance_data)

    return performance_data


def add_default_wsi_dimensions(performance_data: dict, file_path: str, **kwargs):
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
    target_dimensions['levels'] = source.getMetadata()['levels']
    target_dimensions['band_count'] = source.getMetadata()['bandCount']

    performance_data['file_dimensions'] = target_dimensions.copy()

    performance_data['slide_dimensions'] = calculate_slide_dimensions(source, **kwargs)

    del source


_FILE_DIMENSION_ATTRS = (
    'tile_width',
    'tile_height',
    'x',
    'y',
    'magnification',
    'levels',
    'band_count',
)

_PERFORMANCE_METRICS = {
    'inference_times': ('run_inference_times', 'aggregated_inference_times'),
    'batch_retreival_times': (
        'run_batch_retreival_times',
        'aggregated_batch_retreival_times',
    ),
    'write_times': ('run_write_times', 'aggregated_write_times'),
}

_SECTION_SUFFIXES = {
    'with_cache': 'with_cache',
    'without_cache': 'without_cache',
    'pytorch_dataset': 'pytorch_dataset',
}


def _set_aggregate_attrs(h5_file: h5py.File, first_run: dict):
    for key in _FILE_DIMENSION_ATTRS:
        h5_file.attrs[key] = first_run['file_dimensions'][key]

    for key, value in first_run['slide_dimensions'].items():
        h5_file.attrs[f'slide_dimensions_{key}'] = value


def _add_array_value(output_data: dict, key: str, value):
    if key not in output_data:
        output_data[key] = np.array([])
    output_data[key] = np.concatenate([output_data[key], np.array([value])])


def _add_run_metric(output_data: dict, run_key: str, aggregate_key: str, values):
    output_data.setdefault(run_key, []).append(values)
    if aggregate_key not in output_data:
        output_data[aggregate_key] = np.array([])
    output_data[aggregate_key] = np.concatenate([output_data[aggregate_key], values])


def _add_energy_metric(output_data: dict, prefix: str, values):
    for index, value in enumerate(values):
        _add_array_value(output_data, f'aggregated_{prefix}_energy_{index}', value)


def _add_energy_data(output_data: dict, run: dict):
    energy_data = run.get('energy_data')
    if not energy_data:
        return

    if 'cpu_energy' in energy_data:
        _add_energy_metric(output_data, 'cpu', energy_data['cpu_energy'].values())
    if 'gpu_energy' in energy_data:
        _add_energy_metric(output_data, 'gpu', energy_data['gpu_energy'])
    if 'dram_energy' in energy_data:
        _add_energy_metric(output_data, 'dram', energy_data['dram_energy'])
    if 'time' in energy_data:
        _add_array_value(output_data, 'aggregated_energy_times', energy_data['time'])


def _add_performance_section(output_data: dict, run: dict, section: str):
    if section not in run:
        return

    section_data = run[section]
    suffix = _SECTION_SUFFIXES[section]
    output_data.setdefault(f'setup_times_{suffix}', []).append(section_data['setup_time'])
    output_data.setdefault(f'process_times_{suffix}', []).append(section_data['process_time'])

    for metric, names in _PERFORMANCE_METRICS.items():
        if metric not in section_data:
            continue
        run_prefix, aggregate_prefix = names
        _add_run_metric(
            output_data,
            f'{run_prefix}_{suffix}',
            f'{aggregate_prefix}_{suffix}',
            section_data[metric],
        )


def _finalize_scalar_lists(output_data: dict):
    for key, value in list(output_data.items()):
        if key.startswith(('setup_times_', 'process_times_')):
            output_data[key] = np.array(value)


def _write_aggregate_datasets(h5_file: h5py.File, output_data: dict):
    for key, data in output_data.items():
        if key.startswith('run_'):
            for index, run_data in enumerate(data):
                if run_data.shape[0] > 0:
                    h5_file.create_dataset(f'{index}_{key}', data=run_data)
        else:
            h5_file.create_dataset(key, data=data)


def aggregate_runs(runs: list[dict], output_file_path: str):
    if len(runs) == 0:
        return None

    file_dir = os.path.dirname(output_file_path)
    os.makedirs(file_dir, exist_ok=True)
    output_data = {}

    with h5py.File(output_file_path, 'w') as f:
        _set_aggregate_attrs(f, runs[0])

        for run in runs:
            _add_energy_data(output_data, run)
            _add_performance_section(output_data, run, 'pytorch_dataset')
            _add_performance_section(output_data, run, 'with_cache')
            _add_performance_section(output_data, run, 'without_cache')

        _finalize_scalar_lists(output_data)
        _write_aggregate_datasets(f, output_data)

    return output_data


def add_performance_data(
    performance_data: dict,
    target_dimensions: dict,
    performance_type: str,
    setup_time: float,
    process_time: float,
    batch_retreival_times: Optional[list[float]] = None,
    inference_times: Optional[list[float]] = None,
    write_times: Optional[list[float]] = None,
):
    if write_times is None:
        write_times = []
    if inference_times is None:
        inference_times = []
    if batch_retreival_times is None:
        batch_retreival_times = []
    performance_entry = {}
    performance_entry['target_dimensions'] = target_dimensions
    performance_entry['setup_time'] = setup_time
    performance_entry['process_time'] = process_time

    if len(batch_retreival_times) > 0:
        batch_retreival_times_array = np.array(batch_retreival_times)
        avg_batch_retreival_time = np.mean(batch_retreival_times_array)
        std_batch_retreival_time = np.std(batch_retreival_times_array)

        performance_entry['inference_times'] = batch_retreival_times_array
        performance_entry['avg_inference_time'] = avg_batch_retreival_time
        performance_entry['std_inference_time'] = std_batch_retreival_time

    if len(inference_times) > 0:
        inference_times_array = np.array(inference_times)
        avg_inference_time = np.mean(inference_times_array)
        std_inference_time = np.std(inference_times_array)

        performance_entry['batch_retreival_times'] = inference_times_array
        performance_entry['avg_batch_retreival_time'] = avg_inference_time
        performance_entry['std_batch_retreival_time'] = std_inference_time

    if len(write_times) > 0:
        write_times_array = np.array(write_times)
        avg_write_time = np.mean(write_times_array)
        std_write_time = np.std(write_times_array)

        performance_entry['write_times'] = write_times_array
        performance_entry['avg_write_time'] = avg_write_time
        performance_entry['std_write_time'] = std_write_time

    performance_data[performance_type] = performance_entry


def run_reproducible_performance_evaluation(
    file_path: str,
    n_runs: int = 3,
    file_dir: Optional[str] = None,
    track_memory: bool = False,
    track_energy: bool = False,
    output_dir: str = './performance',
    without_cache: bool = False,
    run_eager: bool = False,
    run_non_eager: bool = False,
    run_dataset: bool = False,
    without_icc: bool = False,
    with_tiff_source: bool = False,
    performance_type: str = 'read',
    compile_model: bool = False,
    **kwargs,
):
    print('Running reproducible performance evaluation with output directory: ', output_dir)
    eager_runs = []
    non_eager_runs = []
    dataset_runs = []

    os.makedirs(output_dir, exist_ok=True)

    eager_output_filename = 'eager_performance_evaluation.h5'
    eager_output_file_path = os.path.join(output_dir, eager_output_filename)

    non_eager_output_filename = 'non_eager_performance_evaluation.h5'
    non_eager_output_file_path = os.path.join(output_dir, non_eager_output_filename)

    dataset_output_filename = 'dataset_performance_evaluation.h5'
    dataset_output_file_path = os.path.join(output_dir, dataset_output_filename)

    if run_dataset:
        if file_dir is None:
            msg = 'file_dir is required when running dataset performance evaluation'
            raise ValueError(msg)
        for i in range(n_runs):
            print(
                f'Running dataset performance evaluation {i + 1} of {n_runs} with kwargs: {kwargs}',
            )
            performance_data = run_dataset_performance_evaluation(
                file_path,
                file_dir,
                performance_type,
                compile_model,
                track_memory,
                track_energy,
                output_dir,
                i,
                **kwargs,
            )
            dataset_runs.append(performance_data)

    if run_eager:
        for i in range(n_runs):
            print(f'Running eager performance evaluation {i + 1} of {n_runs} with kwargs: {kwargs}')
            performance_data = run_eager_performance_evaluation(
                file_path,
                without_cache,
                without_icc,
                with_tiff_source,
                performance_type,
                compile_model,
                track_memory,
                track_energy,
                output_dir,
                i,
                **kwargs,
            )
            eager_runs.append(performance_data)

    if run_non_eager:
        for i in range(n_runs):
            print(
                f'Running non-eager performance evaluation {i + 1} of {n_runs} '
                f'with kwargs: {kwargs}',
            )
            performance_data = run_non_eager_performance_evaluation(
                file_path,
                without_cache,
                without_icc,
                with_tiff_source,
                performance_type,
                compile_model,
                track_memory,
                track_energy,
                output_dir,
                i,
                **kwargs,
            )
            non_eager_runs.append(performance_data)

    eager_runs = aggregate_runs(eager_runs, eager_output_file_path)
    non_eager_runs = aggregate_runs(non_eager_runs, non_eager_output_file_path)
    dataset_runs = aggregate_runs(dataset_runs, dataset_output_file_path)

    return eager_runs, non_eager_runs, dataset_runs


def run_multi_slide_performance_evaluation():
    os.path.join('/scr/arosado/')


def make_directory_performance_output_paths(output_dir: str, base_filename: str):
    output_paths = []
    for runner_name in ['eager', 'non_eager']:
        for model_name in ['sobel', 'efficientnetb0', 'uni2', 'uni']:
            output_paths.append(
                os.path.join(
                    output_dir,
                    f'{base_filename}_{runner_name}_performance_{model_name}.h5',
                ),
            )
    return output_paths


def run_performance_testing_on_directory(
    directory: str,
    file_extensions: list[str] = None,
    performance_types: list[str] = None,
    track_class_memory: bool = False,
    output_dir: str = './performance',
    n_runs: int = 1,
    n_files: int = 1,
    **kwargs,
):
    if performance_types is None:
        performance_types = [
            'read',
            'write',
            'inference_sobel',
            'inference_efficientnetb0',
            'inference_uni2',
        ]
    if file_extensions is None:
        file_extensions = ['.tif', '.svs', '.mrxs', '.ndpi']
    os.makedirs(output_dir, exist_ok=True)

    file_count = 0
    for root, _dirs, files in os.walk(directory):
        for file in files:
            if file_count >= n_files:
                break
            if not file.endswith(tuple(file_extensions)):
                continue

            file_count += 1
            file_path = os.path.join(root, file)
            base_filename = os.path.basename(file_path)
            output_paths = make_directory_performance_output_paths(output_dir, base_filename)

            print('Starting performance evaluation for file: ', file_path)
            if all(os.path.exists(output_path) for output_path in output_paths):
                print(
                    f'Skipping performance evaluation for file: {file_path} '
                    'because output files already exist',
                )
                continue

            print(f'Finished performance evaluation for file: {file_path}')


def run_batch_size(tile_source: large_image.tilesource, batch_size: int = 64):
    metadata = tile_source.getMetadata()
    tile_size = {'width': 16, 'height': 16}
    tile_range_x = int(np.ceil(metadata['sizeX'] / tile_size['width']))
    tile_range_y = int(np.ceil(metadata['sizeY'] / tile_size['height']))
    total_tiles = tile_range_x * tile_range_y
    assert batch_size <= total_tiles
    tiles = np.array(
        [[idx // tile_range_x, idx % tile_range_x] for idx in range(batch_size)],
        dtype=np.float32,
    )
    iterator = tile_source.eagerIterator(
        output_mode='tiles',
        tiles=tiles,
        tile_size=tile_size,
        chunk_mult=8,
        batch=batch_size,
        prefetch=1,
        workers=2,
    )
    try:
        batch = next(iterator)
        shared_tiles = batch['tile']
        batch_images = None
        try:
            batch_images = shared_tiles.view()
            batch_shape = batch_images.shape
            batch_image = batch_images[0].copy()
            batch_image_copy = batch_image[:]
            assert batch_shape[0] == batch_size
            assert len(batch_shape) == 4
            assert np.all(batch_image == batch_image_copy)
        finally:
            del batch_images
            shared_tiles.close()
    finally:
        iterator.cleanup(wait=True)
        del iterator


def build_numpy_shared_array(
    array_shape: tuple[int, int, int] = (256, 256, 3),
    dtype: np.dtype = np.uint8,
    is_torch: bool = False,
):
    shared_array = SharedArray(array_shape, dtype, is_torch)
    return shared_array


def build_torch_shared_array(
    array_shape: tuple[int, int, int] = (256, 256, 3),
    dtype: torch.dtype = torch.uint8,
    is_torch: bool = True,
):
    shared_array = SharedArray(array_shape, dtype, is_torch)
    return shared_array


def run_eager_iterator_with_albumentations_transform(
    tile_source: large_image.tilesource,
    transform: A.Compose,
    region: dict[str, Any] | None = None,
):
    try:
        start_time = time.time()
        if region is None:
            region = copy_eager_test_region()
        iterator = tile_source.eagerIterator(
            output_mode='tiles', transform=transform, region=region,
        )
        # Count output images provided by the iterator
        output_image_count = iterator.get_output_image_count()
        # Count tiles provided by the iterator based on the slide dimensions if a
        # subset not selected
        tile_image_count = (
            iterator.slide_dimensions['tile_target_range_x'] *
            iterator.slide_dimensions['tile_target_range_y']
        )

        # Count tiles provided by the iterator
        count = 0
        for batch in iterator:
            batch_images = batch['tile'].view()
            count += batch_images.shape[0]

        del iterator

        end_time = time.time()
        print(f'Time taken: {end_time - start_time} seconds')

        return output_image_count, tile_image_count, count

    except Exception as e:
        raise e


def run_eager_iterator_numpy_dtype(test_file: Any, dtype: np.dtype):
    metadata = large_image.open(test_file).getMetadata()
    region = {
        'left': 0,
        'top': 0,
        'width': min(metadata['sizeX'], metadata['tileWidth']),
        'height': min(metadata['sizeY'], metadata['tileHeight']),
        'units': 'base_pixels',
    }
    source, iterator = build_eager_iterator(
        test_file, dtype=dtype, region=region, workers=2, prefetch=1,
    )
    try:
        for batch in iterator:
            batch_images = batch['tile'].view()
            assert batch_images.dtype == dtype, f'Expected {dtype}, got {batch_images.dtype}'
    finally:
        del iterator


def build_eager_iterator(
    test_file: Any,
    scale_mode: str = 'mag',
    target_scale: Union[float, tuple[float, float]] = 20,
    tile_size: tuple[int, int] = (224, 224),
    overlap: float = 0,
    chunk_mult: int = 4,
    mask: str = None,
    output_mode: str = 'tiles',
    transform: Callable = None,
    dtype: np.dtype = np.uint8,
    batch: int = 64,
    region: dict = None,
    workers: int = 16,
    prefetch: int = 16,
):
    source = large_image.open(test_file)
    if scale_mode == 'mag':
        scale = {'magnification': target_scale}
    elif scale_mode == 'mm':
        if isinstance(target_scale, tuple):
            scale = {'mm_x': target_scale[0], 'mm_y': target_scale[1]}
        else:
            scale = {'mm_x': target_scale, 'mm_y': target_scale}
    else:
        msg = "scale_mode must be either 'mag' or 'mm'"
        raise ValueError(msg)

    iterator = source.eagerIterator(
        scale=scale,
        tile_size={'width': tile_size[0], 'height': tile_size[1]},
        tile_overlap={'x': overlap, 'y': overlap},
        chunk_mult=chunk_mult,
        mask=mask,
        output_mode=output_mode,
        transform=transform,
        batch=batch,
        dtype=dtype,
        region=region,
        workers=workers,
        prefetch=prefetch,
    )
    return source, iterator


@pytest.fixture(scope='module')
def test_eager_iterator_image(
    test_file: Any,
    output_dir_path: Union[str, Path],
    target_scale: int,
    tile_size: tuple[int, int],
):
    source, iterator = build_eager_iterator(
        test_file,
        target_scale=target_scale,
        tile_size=tile_size,
    )

    thumbnail, _ = source.getThumbnail(size=(1024, 1024), format='numpy')
    thumbnail_output_path = os.path.join(output_dir_path, 'thumbnail.png')
    plt.imsave(thumbnail_output_path, thumbnail)

    test_large_image = np.zeros(
        (
            iterator.slide_dimensions['tile_target_range_y'] * tile_size[1],
            iterator.slide_dimensions['tile_target_range_x'] * tile_size[0],
            3,
        ),
        dtype=np.uint8,
    )
    for batch in iterator:
        batch_images = batch['tile'].view()
        batch_read_kwargs = batch
        for i in range(batch_images.shape[0]):
            x = int(batch_read_kwargs['tile_position']['region_x'][i].item())
            y = int(batch_read_kwargs['tile_position']['region_y'][i].item())
            image = batch_images[i]
            test_large_image[
                y * tile_size[1]: (y + 1) * tile_size[1],
                x * tile_size[0]: (x + 1) * tile_size[0],
                :,
            ] = image[:, :, :]

    large_image_output_path = os.path.join(output_dir_path, 'large_image.png')
    plt.imsave(large_image_output_path, test_large_image)
    del iterator


def run_eager_iterator_with_pytorch_transform(
    tile_source: large_image.tilesource,
    transform: Callable,
    region: dict[str, Any] | None = None,
):
    start_time = time.time()
    if region is None:
        region = copy_eager_test_region()
    iterator = tile_source.eagerIterator(
        output_mode='tiles', transform=transform, region=region,
    )

    # Count output images provided by the iterator
    output_image_count = iterator.get_output_image_count()
    # Count tiles provided by the iterator based on the slide dimensions if a subset not selected
    tile_image_count = (
        iterator.slide_dimensions['tile_target_range_x'] *
        iterator.slide_dimensions['tile_target_range_y']
    )

    # Count tiles provided by the iterator
    count = 0
    for batch in iterator:
        batch_images = batch['tile'].view()
        count += batch_images.shape[0]

    del iterator

    end_time = time.time()
    print(f'Time taken: {end_time - start_time} seconds')

    return output_image_count, tile_image_count, count


def thresh_hsl(thresh_img):
    if thresh_img.shape[2] == 3:
        thresh_img = cv2.cvtColor(thresh_img, cv2.COLOR_RGB2HLS)
    elif thresh_img.shape[2] == 4:
        thresh_img = cv2.cvtColor(thresh_img, cv2.COLOR_RGBA2RGB)
        thresh_img = cv2.cvtColor(thresh_img, cv2.COLOR_RGB2HLS)
    else:
        msg = 'Image must be RGB or RGBA'
        raise ValueError(msg)

    # Attempt to remove the white background using a statistical approach

    mean_lightness = np.mean(thresh_img[:, :, 1])
    std_lightness = np.std(thresh_img[:, :, 1])

    mean_hue = np.mean(thresh_img[:, :, 0])
    np.std(thresh_img[:, :, 0])

    mean_sat = np.mean(thresh_img[:, :, 2])
    np.std(thresh_img[:, :, 2])

    lightness_cutoff = None
    if mean_lightness + (std_lightness * 2) >= 245:
        lightness_cutoff = 245
    else:
        lightness_cutoff = mean_lightness

    thresh_img[(thresh_img[:, :, 1] >= lightness_cutoff)] = [0, 0, 0]

    # Assume if hue is greater than mean hue, then it is a non-background tile

    grey = thresh_img[:, :, 1]
    grey[(thresh_img[:, :, 0] > mean_hue) & (thresh_img[:, :, 2] > mean_sat)] = 255

    return thresh_img, grey


def get_tissue_mask_with_background_elimination(
    img,
    return_polygons=False,
    threshold_contour_areas=None,
    debug_output_path=None,
    slide_dimensions=None,
):
    if threshold_contour_areas is None:
        threshold_contour_areas = [0.0001, 5e-05]
    thresh = img.copy()

    thresh, gray = thresh_hsl(thresh)

    kernel = np.ones((3, 3), np.uint8)
    gray = cv2.dilate(gray, kernel, iterations=1)
    thresh_after = cv2.threshold(gray, 5, 250, cv2.THRESH_OTSU)[1]
    # thresh_after = cv2.bitwise_not(thresh_after)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    morph = cv2.morphologyEx(
        thresh_after,
        cv2.MORPH_OPEN,
        kernel,
        borderType=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    morph = cv2.morphologyEx(
        morph,
        cv2.MORPH_CLOSE,
        kernel,
        borderType=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    morph = cv2.morphologyEx(
        morph,
        cv2.MORPH_ERODE,
        kernel,
        borderType=cv2.BORDER_CONSTANT,
        borderValue=0,
    )

    # Find contours that are relevant in the image
    polygons = []
    contours, hierarchy = cv2.findContours(morph, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    contour_mask = np.zeros_like(gray)
    contour_count = 0
    for threshold in threshold_contour_areas:
        for contour_count, contour in enumerate(contours):
            contour_area = cv2.contourArea(contour)
            if contour_area > threshold * (img.shape[0] * img.shape[1]):
                # Check if this is an outer contour (parent is -1) or inner contour (hole)
                if hierarchy[0][contour_count, 3] == -1:  # Outer contour
                    cv2.drawContours(contour_mask, [contour], 0, 255, -1)
                elif hierarchy[0][contour_count, 3] != -1:  # Inner contour (hole)
                    cv2.drawContours(contour_mask, [contour], 0, 0, -1)

                if return_polygons:
                    from shapely import affinity, to_geojson
                    from shapely.geometry import Polygon

                    polygon = Polygon(np.squeeze(contour))
                    if slide_dimensions is not None:
                        polygon = affinity.scale(
                            polygon,
                            xfact=(slide_dimensions['base_size_x'] / thresh.shape[1]),
                            yfact=(slide_dimensions['base_size_y'] / thresh.shape[0]),
                            origin=(0, 0),
                        )
                    polygons.append(to_geojson(polygon))

    blur = cv2.GaussianBlur(contour_mask, (5, 5), sigmaX=0, sigmaY=0, borderType=cv2.BORDER_DEFAULT)

    if debug_output_path is not None:
        print('Saving original image {}'.format(img.shape))
        img_out_path = os.path.join(debug_output_path, 'test_original.png')
        plt.imsave(img_out_path, img)

        print('Saving threshold before {}'.format(thresh.shape))
        img_out_path = os.path.join(debug_output_path, 'test_threshold_before.png')
        plt.imsave(img_out_path, thresh)

        print('Saving thresh hue {}'.format(thresh[:, :, 0].shape))
        img_out_path = os.path.join(debug_output_path, 'test_threshold_hue.png')
        plt.imsave(img_out_path, thresh[:, :, 0])

        print('Saving thresh lightness {}'.format(thresh[:, :, 1].shape))
        img_out_path = os.path.join(debug_output_path, 'test_threshold_lightness.png')
        plt.imsave(img_out_path, thresh[:, :, 1])

        print('Saving thresh sat {}'.format(thresh[:, :, 2].shape))
        img_out_path = os.path.join(debug_output_path, 'test_threshold_saturation.png')
        plt.imsave(img_out_path, thresh[:, :, 2])

        print('Saving grayscale after {}'.format(gray.shape))
        img_out_path = os.path.join(debug_output_path, 'test_gray.png')
        plt.imsave(img_out_path, gray)

        print('Saving threshold after {}'.format(thresh_after.shape))
        img_out_path = os.path.join(debug_output_path, 'test_threshold_after.png')
        plt.imsave(img_out_path, thresh_after)

        print('Saving morph {}'.format(morph.shape))
        img_out_path = os.path.join(debug_output_path, 'test_morph.png')
        plt.imsave(img_out_path, morph)

        print('Saving contour mask {}'.format(contour_mask.shape))
        img_out_path = os.path.join(debug_output_path, 'test_contour_mask.png')
        plt.imsave(img_out_path, contour_mask)

        print('Saving blur {}'.format(blur.shape))
        img_out_path = os.path.join(debug_output_path, 'test_blur.png')
        plt.imsave(img_out_path, blur)

    if return_polygons:
        return blur, polygons
    return blur, None
