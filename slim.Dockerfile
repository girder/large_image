# Build wheels
FROM python:3.9-slim as build

# Need git for setuptools_scm
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*

COPY . /opt/build-context/
WORKDIR /opt/build-context

RUN python -m pip install --upgrade pip wheel setuptools
RUN sh .circleci/make_wheels.sh
RUN mv ~/wheels /opt/build-context/

# Production
FROM python:3.9-slim

COPY --from=build /opt/build-context/wheels /opt/wheels
LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"
LABEL repo="https://github.com/girder/large_image"
# NOTE: this does not install any girder3 packages
RUN pip install \
    --find-links https://girder.github.io/large_image_wheels \
    --find-links=/opt/wheels \
    'pylibmc>=1.5.1' \
    matplotlib \
    pyvips \
    simplejpeg \
    $(ls -1  /opt/wheels/large_image*.whl)
