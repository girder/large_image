import itertools
import os

from setuptools import setup

try:
    from setuptools_scm import get_version

    version = get_version()
    limit_version = f'>={version}' if '+' not in version and not os.getenv('TOX_ENV_NAME') else ''
except (ImportError, LookupError):
    limit_version = ''

with open('README.rst') as readme_file:
    readme = readme_file.read()
description = 'Python modules to work with large, multiresolution images.'
long_description = readme

extraReqs = {
    'memcached': ['pylibmc>=1.5.1 ; platform_system != "Windows"'],
    'redis': ['redis>=4.5.5'],
    'converter': [f'large-image-converter{limit_version}'],
    'colormaps': ['matplotlib', 'tol_colors'],
    'jupyter': ['aiohttp', 'ipyvue', 'ipyleaflet'],
    'tiledoutput': ['pyvips'],
    'performance': [
        'psutil>=4.2.0',
        'simplejpeg',
    ],
}
sources = {
    'bioformats': [f'large-image-source-bioformats{limit_version}'],
    'deepzoom': [f'large-image-source-deepzoom{limit_version}'],
    'dicom': [f'large-image-source-dicom{limit_version}'],
    'dummy': [f'large-image-source-dummy{limit_version}'],
    'gdal': [f'large-image-source-gdal{limit_version}'],
    'mapnik': [f'large-image-source-mapnik{limit_version}'],
    'multi': [f'large-image-source-multi{limit_version}'],
    'nd2': [f'large-image-source-nd2{limit_version}'],
    'ometiff': [f'large-image-source-ometiff{limit_version}'],
    'openjpeg': [f'large-image-source-openjpeg{limit_version}'],
    'openslide': [f'large-image-source-openslide{limit_version}'],
    'pil': [f'large-image-source-pil{limit_version}'],
    'rasterio': [f'large-image-source-rasterio{limit_version}'],
    'test': [f'large-image-source-test{limit_version}'],
    'tiff': [f'large-image-source-tiff{limit_version}'],
    'tifffile': [f'large-image-source-tifffile{limit_version}'],
    'vips': [f'large-image-source-vips{limit_version}'],
    'zarr': [f'large-image-source-zarr{limit_version}'],
}
extraReqs.update(sources)
extraReqs['sources'] = list(set(itertools.chain.from_iterable(sources.values())))
extraReqs['all'] = list(set(itertools.chain.from_iterable(extraReqs.values())) | {
    f'large-image-source-multi[all]{limit_version}',
    f'large-image-source-pil[all]{limit_version}',
    f'large-image-source-rasterio[all]{limit_version}',
    f'large-image-source-tiff[all]{limit_version}',
})
# The common packages are ones that will install on Ubuntu, OSX, and Windows
# from pypi with all needed dependencies.
extraReqs['common'] = list(set(itertools.chain.from_iterable(extraReqs[key] for key in {
    'colormaps', 'performance',
    'deepzoom', 'dicom', 'multi', 'nd2', 'openslide', 'test', 'tifffile',
    'zarr',
})) | {
    f'large-image-source-pil[common]{limit_version}',
    f'large-image-source-rasterio[all]{limit_version}',
})

setup(
    name='large-image',
    description=description,
    long_description=long_description,
    long_description_content_type='text/x-rst',
    license='Apache-2.0',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
    install_requires=[
        'cachetools',
        'palettable',
        'Pillow>=10.3',
        'numpy',
        'typing-extensions',
    ],
    extras_require=extraReqs,
    include_package_data=True,
    keywords='large_image',
    packages=['large_image'],
    url='https://github.com/girder/large_image',
    zip_safe=False,
)
