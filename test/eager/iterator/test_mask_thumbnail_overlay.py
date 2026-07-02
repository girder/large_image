import argparse
from pathlib import Path

import numpy as np
from PIL import Image

import large_image

try:
    import pytest
except ImportError:
    pytest = None


def _singular_test(func):
    if pytest is None:
        return func
    return pytest.mark.singular(func)


def _read_kwargs_array(iterator):
    rows = [np.asarray(chunk) for chunk in iterator.read_kwargs if len(chunk)]
    if not rows:
        return np.empty((0, 10), dtype=np.float32)
    return np.vstack(rows)


def _make_eager_iterator(
    source,
    mask_file,
    tile_size,
    target_magnification,
    area_threshold,
    threshold_mask,
):
    return source.eagerIterator(
        scale={'magnification': target_magnification},
        tile_size={'width': tile_size, 'height': tile_size},
        mask=mask_file,
        area_threshold=area_threshold,
        threshold_mask=threshold_mask,
        batch=64,
        prefetch=0,
        workers=2,
    )


def write_eager_mask_thumbnail_overlay(
    image_file,
    mask_file,
    output_file,
    tile_size=224,
    target_magnification=20,
    area_threshold=0.25,
    threshold_mask=100,
    thumbnail_size=1024,
):
    from matplotlib import pyplot as plt
    from matplotlib.patches import Rectangle

    image_file = Path(image_file)
    mask_file = Path(mask_file)
    output_file = Path(output_file)

    assert image_file.exists(), f'Image file does not exist: {image_file}'
    assert mask_file.exists(), f'Mask file does not exist: {mask_file}'

    source = large_image.open(str(image_file))
    iterator = _make_eager_iterator(
        source,
        str(mask_file),
        tile_size,
        target_magnification,
        area_threshold,
        threshold_mask,
    )
    try:
        read_kwargs = _read_kwargs_array(iterator)
        slide_dimensions = iterator.slide_dimensions
    finally:
        iterator.cleanup(wait=False)
        del iterator

    assert read_kwargs.size, 'The eager iterator did not plan any tiles for this mask.'

    thumbnail, _ = source.getThumbnail(size=(thumbnail_size, thumbnail_size), format='numpy')
    thumb_height, thumb_width = thumbnail.shape[:2]
    scale_x = thumb_width / slide_dimensions['base_size_x']
    scale_y = thumb_height / slide_dimensions['base_size_y']

    fig_width = max(6, thumb_width / 160)
    fig_height = max(6, thumb_height / 160)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), constrained_layout=True)
    ax.imshow(thumbnail)
    ax.set_axis_off()
    ax.set_title(
        f'{image_file.name} - {len(read_kwargs)} eager tiles from {mask_file.name}',
        fontsize=10,
    )

    for row in read_kwargs:
        top = float(row[4])
        bottom = float(row[5])
        left = float(row[6])
        right = float(row[7])
        ax.add_patch(
            Rectangle(
                (left * scale_x, top * scale_y),
                (right - left) * scale_x,
                (bottom - top) * scale_y,
                fill=False,
                edgecolor='tab:red',
                linewidth=0.8,
                alpha=0.85,
            ),
        )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_file, dpi=160)
    plt.close(fig)

    mask = np.array(Image.open(mask_file).convert('L'))
    assert mask.size > 0
    return output_file


@_singular_test
def test_eager_mask_thumbnail_overlay(request):
    image_file = request.config.getoption('--eager-image-file')
    mask_file = request.config.getoption('--eager-mask-file')
    output_file = request.config.getoption('--eager-overlay-output')

    if not image_file or not mask_file:
        pytest.skip(
            'Skipping eager mask overlay test; matched image and mask files are not '
            'available in the default testing setup. Pass --eager-image-file and '
            '--eager-mask-file to run it.',
        )
    if not Path(image_file).exists() or not Path(mask_file).exists():
        pytest.skip(
            'Skipping eager mask overlay test; the supplied matched image and mask '
            'files are not available in this testing setup.',
        )

    output_path = write_eager_mask_thumbnail_overlay(image_file, mask_file, output_file)
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def _build_parser():
    parser = argparse.ArgumentParser(
        description='Generate a thumbnail overlay showing mask-filtered eager iterator tiles.',
    )
    parser.add_argument('--image-file', required=True)
    parser.add_argument('--mask-file', required=True)
    parser.add_argument(
        '--output-file',
        default='build/eager_mask_thumbnail_overlay.png',
    )
    parser.add_argument('--tile-size', type=int, default=224)
    parser.add_argument('--target-magnification', type=float, default=20)
    parser.add_argument('--area-threshold', type=float, default=0.25)
    parser.add_argument('--threshold-mask', type=float, default=100)
    parser.add_argument('--thumbnail-size', type=int, default=1024)
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    output_path = write_eager_mask_thumbnail_overlay(
        image_file=args.image_file,
        mask_file=args.mask_file,
        output_file=args.output_file,
        tile_size=args.tile_size,
        target_magnification=args.target_magnification,
        area_threshold=args.area_threshold,
        threshold_mask=args.threshold_mask,
        thumbnail_size=args.thumbnail_size,
    )
    print(output_path)


if __name__ == '__main__':
    main()
