#!/bin/bash

set -e

ROOTPATH=`pwd`

export SETUPTOOLS_SCM_PRETEND_VERSION=`python -m setuptools_scm | sed "s/.* //"`
if [ ${CIRCLE_BRANCH-:} = "master" ]; then
    export SETUPTOOLS_SCM_PRETEND_VERSION=`echo $SETUPTOOLS_SCM_PRETEND_VERSION | sed "s/\+.*$//"`
elif [ "${CIRCLE_BRANCH-:}" == "girder-5" ]; then
    pip install setuptools-scm
    export SETUPTOOLS_SCM_PRETEND_VERSION=$(python -c "import setuptools_scm,re;print(re.sub(r'(\d+\.\d+\.\d+\.)dev(\d+)(\+.*$)', r'\1a\2', setuptools_scm.get_version()))")
fi

python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/girder"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/girder_annotation"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/utilities/converter"
# cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/utilities/tasks"
# cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/bioformats"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/deepzoom"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/dicom"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/dummy"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/gdal"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/mapnik"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/multi"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/nd2"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/ometiff"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/openjpeg"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/openslide"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/pil"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/rasterio"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/test"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/tiff"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/tifffile"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/vips"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
cd "$ROOTPATH/sources/zarr"
cp "$ROOTPATH/README.rst" .
cp "$ROOTPATH/LICENSE" .
python setup.py sdist
pip wheel . --no-deps -w dist
twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) dist/*
