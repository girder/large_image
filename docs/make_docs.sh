#!/usr/bin/env bash

set -e

cd "$(dirname $0)"
stat make_docs.sh

# git clean -fxd .

mkdir -p ../build/docs-work
mkdir -p ../build/docs

rm _build 2>/dev/null || true
ln -s ../build/docs-work _build

large_image_converter --help > _build/large_image_converter.txt

sphinx-apidoc -f -o _build/large_image ../large_image
sphinx-apidoc -f -o _build/large_image_source_bioformats ../sources/bioformats/large_image_source_bioformats
sphinx-apidoc -f -o _build/large_image_source_deepzoom ../sources/deepzoom/large_image_source_deepzoom
sphinx-apidoc -f -o _build/large_image_source_dummy ../sources/dummy/large_image_source_dummy
sphinx-apidoc -f -o _build/large_image_source_gdal ../sources/gdal/large_image_source_gdal
sphinx-apidoc -f -o _build/large_image_source_mapnik ../sources/mapnik/large_image_source_mapnik
sphinx-apidoc -f -o _build/large_image_source_nd2 ../sources/nd2/large_image_source_nd2
sphinx-apidoc -f -o _build/large_image_source_ometiff ../sources/ometiff/large_image_source_ometiff
sphinx-apidoc -f -o _build/large_image_source_openjpeg ../sources/openjpeg/large_image_source_openjpeg
sphinx-apidoc -f -o _build/large_image_source_openslide ../sources/openslide/large_image_source_openslide
sphinx-apidoc -f -o _build/large_image_source_pil ../sources/pil/large_image_source_pil
sphinx-apidoc -f -o _build/large_image_source_test ../sources/test/large_image_source_test
sphinx-apidoc -f -o _build/large_image_source_tiff ../sources/tiff/large_image_source_tiff
sphinx-apidoc -f -o _build/large_image_converter ../utilities/converter/large_image_converter
sphinx-apidoc -f -o _build/large_image_tasks ../utilities/tasks/large_image_tasks
sphinx-apidoc -f -o _build/girder_large_image ../girder/girder_large_image
sphinx-apidoc -f -o _build/girder_large_image_annotation ../girder_annotation/girder_large_image_annotation

sphinx-build -b html . ../build/docs

rm _build || true

cp -r ../.circleci ../build/docs/.
