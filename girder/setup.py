import os

from setuptools import find_packages, setup

description = 'A Girder plugin to work with large, multiresolution images.'
long_description = description + '\n\nSee the large-image package for more details.'


try:
    from setuptools_scm import get_version

    version = get_version(root='..')
    limit_version = f'>={version}' if '+' not in version and not os.getenv('TOX_ENV_NAME') else ''
except (ImportError, LookupError):
    limit_version = ''

setup(
    name='girder-large-image',
    description=description,
    long_description=long_description,
    long_description_content_type='text/x-rst',
    license='Apache-2.0',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
    install_requires=[
        'girder>=3.1.18',
        'girder-jobs>=3.0.3',
        f'large_image{limit_version}',
    ],
    extras_require={
        'tasks': [
            f'large-image-tasks[girder]{limit_version}',
            'girder-worker[girder]>=0.6.0',
        ],
    },
    include_package_data=True,
    keywords='girder-plugin, large_image',
    packages=find_packages(exclude=['test', 'test.*', 'test_girder', 'test_girder.*']),
    python_requires='>=3.8',
    url='https://github.com/girder/large_image',
    zip_safe=False,
    entry_points={
        'girder.plugin': [
            'large_image = girder_large_image:LargeImagePlugin',
        ],
    },
)
