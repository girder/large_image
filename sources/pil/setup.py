import os

from setuptools import find_packages, setup

description = 'A Pillow tilesource for large_image.'
long_description = description + '\n\nSee the large-image package for more details.'


try:
    from setuptools_scm import get_version

    version = get_version(root='../..')
    limit_version = f'>={version}' if '+' not in version and not os.getenv('TOX_ENV_NAME') else ''
except (ImportError, LookupError):
    limit_version = ''

setup(
    name='large-image-source-pil',
    description=description,
    long_description=long_description,
    long_description_content_type='text/x-rst',
    license='Apache-2.0',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
    install_requires=[
        f'large-image{limit_version}',
    ],
    extras_require={
        'all': [
            'rawpy',
            'pillow-heif',
            'pillow-jxl-plugin < 1.3 ; python_version < "3.8"',
            'pillow-jxl-plugin ; python_version >= "3.9"',
            'pillow-jpls',
        ],
        'girder': f'girder-large-image{limit_version}',
    },
    keywords='large_image, tile source',
    packages=find_packages(exclude=['test', 'test.*']),
    url='https://github.com/girder/large_image',
    python_requires='>=3.8',
    entry_points={
        'large_image.source': [
            'pil = large_image_source_pil:PILFileTileSource',
        ],
        'girder_large_image.source': [
            'pil = large_image_source_pil.girder_source:PILGirderTileSource',
        ],
    },
)
