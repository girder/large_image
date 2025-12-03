import os

from setuptools import find_packages, setup

with open('README.rst') as fh:
    readme = fh.read()

description = 'Girder Worker tasks for Large Image.'
long_description = readme


try:
    from setuptools_scm import get_version

    version = get_version(root='../..')
    limit_version = f'>={version}' if '+' not in version and not os.getenv('TOX_ENV_NAME') else ''
except (ImportError, LookupError):
    limit_version = ''

setup(
    name='large-image-tasks',
    description=description,
    long_description=long_description,
    long_description_content_type='text/x-rst',
    license='Apache-2.0',
    author='Kitware Inc',
    author_email='kitware@kitware.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Topic :: Scientific/Engineering',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
    ],
    python_requires='>=3.9',
    install_requires=[
        # Packages required by both producer and consumer side installations
    ],
    extras_require={
        'girder': [
            # Dependencies required on the producer (Girder) side.
            f'large-image-converter{limit_version}',
            'girder-worker[girder]>=5.0.0a10',
        ],
        'worker': [
            # Dependencies required on the consumer (Girder Worker) side.
            f'large-image-converter[sources]{limit_version}',
            'girder-worker[worker]>=5.0.0a10',
        ],
    },
    entry_points={
        'girder_worker_plugins': [
            'large_image_tasks = large_image_tasks:LargeImageTasks',
        ],
    },
    packages=find_packages(),
)
