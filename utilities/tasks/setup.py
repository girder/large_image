import os

from setuptools import find_packages, setup

with open('README.rst') as fh:
    readme = fh.read()

description = 'Girder Worker tasks for Large Image.'
long_description = readme


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


try:
    from setuptools_scm import get_version

    version = get_version(root='../..', local_scheme=prerelease_local_scheme)
    limit_version = f'>={version}' if '+' not in version else ''
except (ImportError, LookupError):
    limit_version = ''

setup(
    name='large-image-tasks',
    use_scm_version={'root': '../..', 'local_scheme': prerelease_local_scheme,
                     'fallback_version': 'development'},
    setup_requires=['setuptools-scm'],
    description=description,
    long_description=long_description,
    license='Apache Software License 2.0',
    author='Kitware Inc',
    author_email='kitware@kitware.com',
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
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    install_requires=[
        # Packages required by both producer and consumer side installations
        'girder-worker-utils>=0.8.5',
        'importlib-metadata<5 ; python_version < "3.8"',
    ],
    extras_require={
        'girder': [
            # Dependencies required on the producer (Girder) side.
            f'large-image-converter{limit_version}',
            'girder-worker[girder]>=0.6.0',
        ],
        'worker': [
            # Dependencies required on the consumer (Girder Worker) side.
            f'large-image-converter[sources]{limit_version}',
            'girder-worker[worker]>=0.6.0',
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
