import os

from setuptools import find_packages, setup

with open('README.rst') as fh:
    long_desc = fh.read()


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
    name='large-image-tasks',
    use_scm_version={'root': '../..', 'local_scheme': prerelease_local_scheme},
    setup_requires=['setuptools-scm'],
    description='Girder Worker tasks for Large Image.',
    long_description=long_desc,
    author='Kitware Inc',
    author_email='kitware@kitware.com',
    license='Apache Software License 2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Scientific/Engineering',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    install_requires=[
        'girder-worker>=0.6.0',
        'girder-worker-utils>=0.8.5',
        # Packages required by both producer and consumer side installations
    ],
    extras_require={
        'girder': [
            # Dependencies required on the producer (Girder) side.
        ],
        'worker': [
            # Dependencies required on the consumer (Girder Worker) side.
            'large-image-converter[sources]',
        ],
    },
    python_requires='>=3.6',
    entry_points={
        'girder_worker_plugins': [
            'large_image_tasks = large_image_tasks:LargeImageTasks',
        ]
    },
    packages=find_packages(),
)
