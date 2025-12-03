import os

from setuptools import find_packages, setup

description = 'A OME Zarr tilesource for large_image.'
long_description = description + '\n\nSee the large-image package for more details.'


try:
    from setuptools_scm import get_version

    version = get_version(root='../..')
    limit_version = f'>={version}' if '+' not in version and not os.getenv('TOX_ENV_NAME') else ''
except (ImportError, LookupError):
    limit_version = ''

setup(
    name='large-image-source-zarr',
    description=description,
    long_description=long_description,
    long_description_content_type='text/x-rst',
    license='Apache-2.0',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
    ],
    python_requires='>=3.9',
    install_requires=[
        f'large-image{limit_version}',
        # Pin zarr < 3.0 due to refactoring of stores:
        # https://github.com/zarr-developers/zarr-python/issues/1274
        'zarr<3',
        # numcodecs and imagecodecs had been required by zarr, but now needs to be asked for
        'imagecodecs',
        # numcodecs had been required by zarr, but now needs to be asked for
        # 0.16 requires zarr 3 (but does specify such)
        'numcodecs<0.16',
        # Without imagecodecs-numcodecs, some jpeg encoded data cannot be read
        'imagecodecs-numcodecs!=2024.9.22',
    ],
    extras_require={
        'girder': f'girder-large-image{limit_version}',
        'all': [
            'large-image-converter',
        ],
    },
    keywords='large_image, tile source',
    packages=find_packages(exclude=['test', 'test.*']),
    url='https://github.com/girder/large_image',
    entry_points={
        'large_image.source': [
            'zarr = large_image_source_zarr:ZarrFileTileSource',
        ],
        'girder_large_image.source': [
            'zarr = large_image_source_zarr.girder_source:ZarrGirderTileSource',
        ],
    },
)
