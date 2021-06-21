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
    name='large-image-converter',
    use_scm_version={'root': '../..', 'local_scheme': prerelease_local_scheme},
    setup_requires=['setuptools-scm'],
    description='Converter for Large Image.',
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
        'gdal',
        'large_image_source_tiff',
        'numpy',
        'psutil',
        'pyvips',
        'tifftools',
    ],
    extras_require={
        'jp2k': [
            'glymur',
        ],
        'sources': [
            'large_image[sources]',
        ],
        'stats': [
            'scikit-image',
        ],
    },
    packages=find_packages(),
    entry_points={
        'console_scripts': ['large_image_converter = large_image_converter.__main__:main']
    },
    python_requires='>=3.6',
)
