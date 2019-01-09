#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools
import os
import platform
import re
from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

extraReqs = {
    'memcached': ['pylibmc>=1.5.1'] if platform.system() != 'Windows' else [],
}
sources = {
    'dummy': ['large-image-source-dummy'],
    'mapnik': ['large-image-source-mapnik'],
    'openslide': ['large-image-source-openslide'],
    'pil': ['large-image-source-pil'],
    'tiff': ['large-image-source-tiff'],
    'test': ['large-image-source-test'],
}
extraReqs.update(sources)
extraReqs['sources'] = list(set(itertools.chain.from_iterable(sources.values())))
extraReqs['all'] = list(set(itertools.chain.from_iterable(extraReqs.values())))

init = os.path.join(os.path.dirname(__file__), 'large_image', '__init__.py')
with open(init) as fd:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
        fd.read(), re.MULTILINE).group(1)

setup(
    name='large_image',
    version=version,
    description='Create, serve, and display large multiresolution images.',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ],
    install_requires=[
        'cachetools>=3.0.0',
        'Pillow>=3.2.0',
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
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*',
    url='https://github.com/girder/large_image',
    zip_safe=False,
)
