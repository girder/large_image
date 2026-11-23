Developer Guide
===============

Developer Installation
----------------------
To install all packages from source, clone the repository::

    git clone https://github.com/girder/large_image.git
    cd large_image

Install all packages and dependencies::

    pip install -e . -r requirements-dev.txt

If you aren't developing with Girder 3, you can skip installing those components.  Use ``requirements-dev-core.txt`` instead of ``requirements-dev.txt``::

    pip install -e . -r requirements-dev-core.txt


Tile Source Requirements
~~~~~~~~~~~~~~~~~~~~~~~~~

Many tile sources have complex prerequisites.  These can be installed directly using your system's package manager or from some prebuilt Python wheels for Linux.  The prebuilt wheels are not official packages, but they can be used by instructing pip to use them by preference::

    pip install -e . -r requirements-dev.txt --find-links https://girder.github.io/large_image_wheels


Test Requirements
~~~~~~~~~~~~~~~~~~

Besides an appropriate version of Python, Large Image tests are run via `tox <https://tox.readthedocs.io/en/latest/>`_.  This is also a convenient way to setup a development environment.

The ``tox`` Python package must be installed:

.. code-block:: bash

   pip install tox

See the tox documentation for how to recreate test environments or perform other maintenance tasks.

By default, instead of storing test environments in a ``.tox`` directory, they are stored in the ``build/tox`` directory.  This is done for convenience in handling build artifacts from Girder-specific tests.

nodejs and npm for Girder Tests or Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``nodejs`` version 22.x or later and a corresponding version of ``npm`` are required to build and test Girder client code.  See `nodejs <https://nodejs.org/en/download/>`_ for how to download and install it.

Mongo for Girder Tests or Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To run the full test suite, including Girder, ensure that a MongoDB instance is ready on ``localhost:27017``.  This can be done with docker via ``docker run -p 27017:27017 -d mongo:latest``.

Running Tests
-------------

Tests are run via tox environments:

.. code-block:: bash

    tox -e test-py39,lint,lintclient

Or, without Girder:

.. code-block:: bash

    tox -e core-py39,lint

You can build the docs.  They are created in the ``docs/build`` directory:

.. code-block:: bash

    tox -e docs

You can run specific tests using pytest's options, e.g., to try one specific test:

.. code-block:: bash

    tox -e core-py39 -- -k testFromTiffRGBJPEG

Girder Web Client Tests
~~~~~~~~~~~~~~~~~~~~~~~

The Girder web client is tested with `Playwright <https://playwright.dev/>`_, following the same structure as Girder's own web client tests.  The tests are in ``girder/girder_large_image/web_client/tests``; each spec in the ``spec`` directory starts its own Girder server (with all installed plugins, including ``large_image_annotation`` and ``dicomweb``) and uses its own MongoDB database, so a MongoDB instance must be running.  The ``test`` tox environments build the web clients, run the Playwright tests, and then run the Python tests.

To run the web client tests directly, the Girder server from the tox environment (or another environment with the plugins installed) must be on the path, and the Playwright browser must be installed once:

.. code-block:: bash

    cd girder/girder_large_image/web_client
    npx playwright install --with-deps chromium
    PATH=../../../build/tox/test-py311/bin:$PATH npm run test

A single spec can be run by naming it (e.g., ``npm run test -- tests/spec/geojs.spec.ts``), and ``npx playwright show-report`` shows the report from the last run.  Some environment variables adjust the tests:

- ``GIRDER_CLIENT_TESTING_MONGO_URI``: the MongoDB server to use (default ``mongodb://localhost:27017``).
- ``GIRDER_CLIENT_TESTING_GIRDER_EXECUTABLE``: the ``girder`` executable to run instead of the one on the path.
- ``GIRDER_CLIENT_TESTING_KEEP_SERVER_ALIVE``: if set, the Girder server and database from each spec are left running after the tests for inspection.
- ``GIRDER_WORKER_TASK_ALWAYS_EAGER``: by default this is ``true`` so that worker tasks (such as processing uploaded annotations) run in the server process; set it to ``false`` to use a message broker and a separate ``celery`` worker.
- ``HEADLESS=false``: show the browser while the tests run.
- ``PLAYWRIGHT_WORKERS`` and ``PLAYWRIGHT_RETRIES``: control parallelism and retries.
- ``DICOMWEB_TEST_URL`` and ``DICOMWEB_TEST_TOKEN``: the DICOMweb tests are skipped unless a DICOMweb server with the CI example data is specified.


Development Environment
-----------------------

To set up a development environment, you can use tox.  This is not required to run tests.  The ``dev`` environment allows for complete use.  The ``test`` environment will also install pytest and other tools needed for testing.  Use the ``core`` environment instead of the ``dev`` environment if you aren't using Girder.

For OSX users, specify the ``dev-osx`` environment instead; it will install only the cross-platform common sources.

You can add a suffix to the environment to get a specific version of python (e.g., ``dev-py311`` or ``dev-osx-py310``.

.. code-block:: bash

   tox --devenv /my/env/path -e dev

and then switch to that environment:

.. code-block:: bash

   . /my/env/path/bin/activate

If you are using Girder, build and start it:

.. code-block:: bash

   girder build --dev
   girder serve
