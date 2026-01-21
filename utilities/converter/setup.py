import os

from setuptools import find_packages, setup

with open('README.rst') as fh:
    readme = fh.read()

description = 'Converter for Large Image.'
long_description = readme


try:
    from setuptools_scm import get_version

    version = get_version(root='../..')
    limit_version = f'>={version}' if '+' not in version and not os.getenv('TOX_ENV_NAME') else ''
except (ImportError, LookupError):
    limit_version = ''

setup(
    name='large-image-converter',
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
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
    ],
    python_requires='>=3.10',
    install_requires=[
        f'large-image-source-tiff{limit_version}',
        'numpy',
        'psutil',
        'pyvips',
        'tifftools',
    ],
    extras_require={
        'jp2k': [
            'glymur',
        ],
        'geospatial': [
            'gdal',
        ],
        'sources': [
            f'large-image[sources]{limit_version}',
        ],
        'stats': [
            'packaging',
            'scikit-image',
        ],
        'all': [
            'glymur',
            'gdal',
            f'large-image[sources]{limit_version}',
            'packaging',
            'scikit-image',
        ],
    },
    packages=find_packages(),
    entry_points={
        'console_scripts': ['large_image_converter = large_image_converter.__main__:main'],
    },
)
