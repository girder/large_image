import os

from setuptools import find_packages, setup

description = 'A OME Zarr tilesource for large_image.'
long_description = description + '\n\nSee the large-image package for more details.'


def prerelease_local_scheme(version):
    """
    Return local scheme version unless building on master in CircleCI.

    This function returns the local scheme version number
    (e.g. 0.0.0.dev<N>+g<HASH>) unless building on CircleCI for a
    pre-release in which case it ignores the hash and produces a
    PEP440 compliant pre-release version number (e.g. 0.0.0.dev<N>).
    """
    from setuptools_scm.version import get_local_node_and_date

    if os.getenv('CIRCLE_BRANCH') in ('master',):
        return ''
    return get_local_node_and_date(version)


try:
    from setuptools_scm import get_version

    version = get_version(root='../..', local_scheme=prerelease_local_scheme)
    limit_version = (
        f'>={version}' if '+' not in version and not os.getenv('TOX_ENV_NAME') else ''
    )
except (ImportError, LookupError):
    limit_version = ''

setup(
    name='large-image-source-zarr',
    use_scm_version={
        'root': '../..',
        'local_scheme': prerelease_local_scheme,
        'fallback_version': '0.0.0',
    },
    description=description,
    long_description=long_description,
    long_description_content_type='text/x-rst',
    license='Apache Software License 2.0',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
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
    python_requires='>=3.6',
    entry_points={
        'large_image.source': [
            'zarr = large_image_source_zarr:ZarrFileTileSource',
        ],
        'girder_large_image.source': [
            'zarr = large_image_source_zarr.girder_source:ZarrGirderTileSource',
        ],
    },
)
