import itertools
import os
import sys

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()
description = 'Python modules to work with large, multiresolution images.'
long_description = readme

extraReqs = {
    'memcached': ['pylibmc>=1.5.1 ; platform_system != "Windows"'],
    'converter': ['large-image-converter'],
    'colormaps': ['matplotlib'],
    'tiledoutput': ['pyvips'],
    'performance': ['simplejpeg'],
}
sources = {
    'bioformats': ['large-image-source-bioformats'],
    'deepzoom': ['large-image-source-deepzoom'],
    'dummy': ['large-image-source-dummy'],
    'gdal': ['large-image-source-gdal'],
    'mapnik': ['large-image-source-mapnik'],
    'multi': ['large-image-source-multi'],
    'ometiff': ['large-image-source-ometiff'],
    'openjpeg': ['large-image-source-openjpeg'],
    'openslide': ['large-image-source-openslide'],
    'pil': ['large-image-source-pil'],
    'test': ['large-image-source-test'],
    'tiff': ['large-image-source-tiff'],
}
if sys.version_info >= (3, 7):
    sources.update({
        'nd2': ['large-image-source-nd2'],
    })
extraReqs.update(sources)
extraReqs['sources'] = list(set(itertools.chain.from_iterable(sources.values())))
extraReqs['all'] = list(set(itertools.chain.from_iterable(extraReqs.values())))


def prerelease_local_scheme(version):
    """
    Return local scheme version unless building on master in CircleCI.

    This function returns the local scheme version number
    (e.g. 0.0.0.dev<N>+g<HASH>) unless building on CircleCI for a
    pre-release in which case it ignores the hash and produces a
    PEP440 compliant pre-release version number (e.g. 0.0.0.dev<N>).
    """
    from setuptools_scm.version import get_local_node_and_date

    if os.getenv('CIRCLE_BRANCH') in ('master', ):
        return ''
    else:
        return get_local_node_and_date(version)


setup(
    name='large-image',
    use_scm_version={'local_scheme': prerelease_local_scheme},
    setup_requires=['setuptools-scm'],
    description=description,
    long_description=long_description,
    license='Apache Software License 2.0',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    install_requires=[
        'cachetools>=3.0.0',
        'palettable',
        # Pillow 8.3.0 and 8.3.1 won't save jpeg compressed tiffs properly.
        'Pillow',
        'psutil>=4.2.0',  # technically optional
        'numpy>=1.10.4',
        'importlib-metadata ; python_version < "3.8"',
    ],
    extras_require=extraReqs,
    include_package_data=True,
    keywords='large_image',
    packages=['large_image'],
    url='https://github.com/girder/large_image',
    python_requires='>=3.6',
    zip_safe=False,
)
