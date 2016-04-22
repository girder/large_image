#! /usr/bin/env python
# -*- coding: utf-8 -*-

import json
import pkg_resources

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
    with open('requirements.txt') as f:
        ireqs = pkg_resources.parse_requirements(f.read())
except pkg_resources.RequirementParseError:
    raise
requirements = [str(req) for req in ireqs]

test_requirements = [
    # TODO: Should we list Girder here?
]

setup(
    name='large_image',
    version=pkginfo['version'],
    description=pkginfo['description'],
    long_description=readme,
    author='Kitware, Inc.',
    author_email='developers@digitalslidearchive.net',
    url='https://github.com/DigitalSlideArchive/large_image',
    packages=[
        'large_image',
        'large_image.server',
    ],
    package_dir={
        'large_image': 'large_image',
        'large_image.server': 'server'
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
    license=license_str,
    # zip_safe=True,  # Let setuptools decide, though it should be zip safe
    keywords='large_image',
    test_suite='plugin_tests',
    tests_require=test_requirements)
