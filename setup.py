#! /usr/bin/env python
# -*- coding: utf-8 -*-

import json
import pkg_resources
import sys

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

try:
    lines = open('requirements.txt').readlines()
    ireqs = pkg_resources.parse_requirements([line for line in lines if not line.startswith('-e ')])
except pkg_resources.RequirementParseError:
    raise
# Don't include pylibmc for Windows
if 'win' in sys.platform:
    ireqs = [req for req in ireqs if req.key not in ('pylibmc', )]
requirements = [str(req) for req in ireqs]

# For lines in requirements.txt that start with -e, store the URL in the
# dependencies (used in dependency_links), and the referenced package in the
# requirements.
dependencies = [line[3:].strip() for line in lines if line.startswith('-e ')]
requirements.extend(['=='.join(entry.split('#egg=')[1].split('-', 1)) for entry in dependencies])


test_requirements = [
    # TODO: Should we list Girder here?
]

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
    entry_points={
        'girder.plugin': 'large_image = large_image.server:load'
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
        'Programming Language :: Python :: 3.4'
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],

    include_package_data=True,
    install_requires=requirements,
    dependency_links=dependencies,
    license=license_str,
    # zip_safe=False,  # Comment out to let setuptools decide
    keywords='large_image',
    test_suite='plugin_tests',
    tests_require=test_requirements)
