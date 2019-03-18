#! /usr/bin/env python
# -*- coding: utf-8 -*-

import json
import platform

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('plugin.json') as f:
    pkginfo = json.load(f)

with open('LICENSE') as f:
    license_str = f.read()

setup(
    name='large_image',
    version=pkginfo['version'],
    description=pkginfo['description'],
    long_description=readme,
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    url='https://github.com/girder/large_image',
    packages=[
        'large_image',
        'large_image.server',
        'large_image.server.cache_util',
        'large_image.server.models',
        'large_image.server.rest',
        'large_image.server.tilesource',
    ],
    data_files=[
        ('large_image/girder', ['plugin.json']),
    ],
    package_dir={
        'large_image': 'large_image',
        'large_image.server': 'server',
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5'
        'Programming Language :: Python :: 3.6'
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    include_package_data=True,
    install_requires=[
        'cachetools>=3.0.0',
        'enum34>=1.1.6',
        'futures; python_version == "2.7"',
        'jsonschema>=2.5.1',
        'libtiff>=0.4.1',
        'numpy>=1.10.2',
        'Pillow>=3.2.0',
        'psutil>=4.2.0',
        'six>=1.10.0',
        'ujson>=1.35',
    ],
    extras_require={
        'memcached': [
            'pylibmc>=1.5.1'
        ] if platform.system() != 'Windows' else [],
        'openslide': [
            'openslide-python>=1.1.0'
        ],
        'mapnik': [
            'mapnik',
            'pyproj',
            'gdal',
            'palettable'
        ]
    },
    license=license_str,
    # zip_safe=False,  # Comment out to let setuptools decide
    keywords='large_image',
    test_suite='plugin_tests')
