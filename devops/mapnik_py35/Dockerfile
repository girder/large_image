FROM geographica/gdal2

COPY ./entrypoint.sh /scripts/entrypoint.sh

WORKDIR /build

# Install Mapnik for Python3
RUN apt-get update && apt-get install -y python3-mapnik \
    git python3-pip

RUN git clone https://github.com/girder/girder.git /build/girder &&  \
    git clone https://github.com/girder/girder_worker.git /build/girder_worker

# Overwrite GIRDER_TEST_DB property
# Mongo host name should be mongodb as opposed to localhost
RUN sed -i 's/localhost:27017/mongodb:27017/g' /build/girder/tests/PythonTests.cmake

RUN pip3 install -e /build/girder && \
    cd /build/girder && pip3 install -r requirements-dev.txt

RUN girder-install plugin -s /build/girder_worker && \
    girder-worker-config set celery broker "amqp:guest:guest@broker"

ENTRYPOINT ["/scripts/entrypoint.sh"]
