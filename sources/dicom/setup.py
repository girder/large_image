import os

from setuptools import find_packages, setup

description = 'A DICOM tilesource for large_image.'
long_description = description + '\n\nSee the large-image package for more details.'


try:
    from setuptools_scm import get_version

    version = get_version(root='../..')
    limit_version = f'>={version}' if '+' not in version and not os.getenv('TOX_ENV_NAME') else ''
except (ImportError, LookupError):
    limit_version = ''

entry_points = {
    'large_image.source': [
        'dicom = large_image_source_dicom:DICOMFileTileSource',
    ],
    'girder_large_image.source': [
        'dicom = large_image_source_dicom.girder_source:DICOMGirderTileSource',
    ],
    'girder.plugin': [
        'dicomweb = large_image_source_dicom.girder_plugin:DICOMwebPlugin',
    ],
}

girder_extras = [
    f'girder-large-image{limit_version}',
    'girder>=5.0.0a10',
]

setup(
    name='large-image-source-dicom',
    description=description,
    long_description=long_description,
    long_description_content_type='text/x-rst',
    license='Apache-2.0',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
    ],
    python_requires='>=3.10',
    install_requires=[
        f'large-image{limit_version}',
        'wsidicom>=0.9.0,!=0.21.3',
        'pydicom<3; python_version < "3.10"',
        'pydicom; python_version >= "3.10"',
    ],
    extras_require={
        'girder': girder_extras,
    },
    include_package_data=True,
    keywords='large_image, tile source',
    packages=find_packages(exclude=['test', 'test.*', 'test_dicom', 'test_dicom.*']),
    url='https://github.com/girder/large_image',
    entry_points=entry_points,
)
