FROM geographica/gdal2

WORKDIR /build

# Install Mapnik for Python3
RUN apt-get update && apt-get install -y python3-mapnik \
    git python3-pip

RUN git clone https://github.com/girder/girder.git /build/girder --single-branch -b 2.x-maintenance

# Overwrite GIRDER_TEST_DB property
# Mongo host name should be mongodb as opposed to localhost
RUN sed -i 's/localhost:27017/mongodb:27017/g' /build/girder/tests/PythonTests.cmake

RUN pip3 install -e /build/girder && \
    pip3 install celery && \
    cd /build/girder && pip3 install -r requirements-dev.txt

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

ENTRYPOINT ["girder-server", "-d", "mongodb://mongodb:27017/girder"]
