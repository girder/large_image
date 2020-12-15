#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup, find_packages


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
    name='girder-large-image',
    use_scm_version={'root': '..', 'local_scheme': prerelease_local_scheme},
    setup_requires=['setuptools-scm', 'setuptools-git'],
    description='A Girder plugin to create, serve, and display large multiresolution images.',
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
    ],
    install_requires=[
        'enum34>=1.1.6;python_version<"3.4"',
        'futures;python_version<"3.4"',
        'girder>=3.0.4',
        'girder-jobs>=3.0.3',
        'girder-worker[girder]>=0.6.0',
        'large_image>=1.0.0',
    ],
    extras_require={
        'tasks': [
            'large-image-tasks',
        ],
    },
    include_package_data=True,
    keywords='girder-plugin, large_image',
    license='Apache Software License 2.0',
    long_description='See the large-image package for more details.',
    packages=find_packages(exclude=['test', 'test.*', 'test_girder', 'test_girder.*']),
    python_requires='>=3.6',
    url='https://github.com/girder/large_image',
    zip_safe=False,
    entry_points={
        'girder.plugin': [
            'large_image = girder_large_image:LargeImagePlugin',
        ]
    },
)
