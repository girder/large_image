#!/bin/bash

# Overwrite the mapnik test configuration for python3
sed -i 's/PY2_ONLY/PY3_ONLY/g' /large_image/plugin.cmake

pip3 install -e /large_image[mapnik]

girder-install plugin -s /large_image
python3 -m girder --host 0.0.0.0 --database mongodb://mongodb:27017/girder
