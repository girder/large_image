#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
from setuptools import setup, find_packages

init = os.path.join(os.path.dirname(__file__), 'large_image_source_tiff', '__init__.py')
with open(init) as fd:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
        fd.read(), re.MULTILINE).group(1)

setup(
    name='large-image-source-tiff',
    version=version,
    description='A TIFF tilesource for large_image',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ],
    install_requires=[
        'large-image>=1.0.0',
        'libtiff>=0.4.1',
    ],
    extras_require={
        'girder': 'girder-large-image>=1.0.0',
    },
    license='Apache Software License 2.0',
    keywords='large_image, tile source',
    packages=find_packages(exclude=['test', 'test.*']),
    url='https://github.com/girder/large_image',
    entry_points={
        'large_image.source': [
            'tiff = large_image_source_tiff:TiffFileTileSource'
        ],
        'girder_large_image.source': [
            'tiff = large_image_source_tiff.girder_source:TiffGirderTileSource'
        ]
    },
)
