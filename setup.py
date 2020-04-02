#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools
import os
import platform
from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

extraReqs = {
    'memcached': ['pylibmc>=1.5.1'] if platform.system() != 'Windows' else [],
}
sources = {
    'dummy': ['large-image-source-dummy'],
    'gdal': ['large-image-source-gdal'],
    'mapnik': ['large-image-source-mapnik'],
    'nd2': ['large-image-source-nd2'],
    'ometiff': ['large-image-source-ometiff'],
    'openjpeg': ['large-image-source-openjpeg'],
    'openslide': ['large-image-source-openslide'],
    'pil': ['large-image-source-pil'],
    'tiff': ['large-image-source-tiff'],
    'test': ['large-image-source-test'],
}
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
    description='Create, serve, and display large multiresolution images.',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    install_requires=[
        'cachetools>=3.0.0',
        # older versions of Pillow probably work but have security issues
        'Pillow>=6.2.2',
        'psutil>=4.2.0',  # technically optional
        'numpy>=1.10.4',
        'six>=1.10.0',
    ],
    extras_require=extraReqs,
    include_package_data=True,
    keywords='large_image',
    license='Apache Software License 2.0',
    long_description=readme,
    packages=find_packages(exclude=['test', 'test.*', 'girder']),
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*',
    url='https://github.com/girder/large_image',
    zip_safe=False,
)
