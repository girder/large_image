import os

from setuptools import find_packages, setup

description = 'A Girder plugin to store and display annotations on large, multiresolution images.'
long_description = description + '\n\nSee the large-image package for more details.'


try:
    from setuptools_scm import get_version

    version = get_version(root='..')
    limit_version = f'>={version}' if '+' not in version and not os.getenv('TOX_ENV_NAME') else ''
except (ImportError, LookupError):
    limit_version = ''

setup(
    name='girder-large-image-annotation',
    use_scm_version={'root': '..',
                     'fallback_version': '0.0.0'},
    description=description,
    long_description=long_description,
    long_description_content_type='text/x-rst',
    license='Apache Software License 2.0',
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
        'jsonschema>=2.5.1',
        f'girder-large-image{limit_version}',
        'orjson',
    ],
    extras_require={
        'compute': [
            'openpyxl',
            'pandas ; python_version < "3.9"',
            'pandas>=2.2 ; python_version >= "3.9"',
            'python-calamine ; python_version >= "3.9"',
            'umap-learn',
        ],
        'tasks': [
            f'girder-large-image[tasks]{limit_version}',
        ],
    },
    include_package_data=True,
    keywords='girder-plugin, large_image',
    packages=find_packages(exclude=['test', 'test.*', 'test_annotation', 'test_annotation.*']),
    python_requires='>=3.8',
    url='https://github.com/girder/large_image',
    zip_safe=False,
    entry_points={
        'girder.plugin': [
            'large_image_annotation = girder_large_image_annotation:LargeImageAnnotationPlugin',
        ],
    },
)
