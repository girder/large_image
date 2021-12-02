Developer Guide
===============

Requirements
------------

Besides an appropriate version of Python, Large Image tests are run via `tox <https://tox.readthedocs.io/en/latest/>`_.  This is also a convenient way to setup a development environment.

The ``tox`` Python package must be installed:

.. code-block:: bash

   pip install tox

See the tox documentation for how to recreate test environments or perform other maintenance tasks.

By default, instead of storing test environments in a ``.tox`` directory, they are stored in the ``build/tox`` directory.  This is done for convenience in handling build artifacts from Girder-specific tests.

nodejs and npm for Girder Tests or Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``nodejs`` version 12.x and a corresponding version of ``npm`` are required to build and test Girder client code.  See `nodejs <https://nodejs.org/en/download/>`_ for how to download and install it.  Remember to get version 12 or earlier.

Mongo for Girder Tests or Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To run the full test suite, including Girder, ensure that a MongoDB instance is ready on ``localhost:27017``.  This can be done with docker via ``docker run -p 27017:27017 -d mongo:latest``.

Running Tests
-------------

Tests are run via tox environments:

.. code-block:: bash

    tox -e test-py39,flake8,lintclient,lintannotationclient

Or, without Girder:

.. code-block:: bash

    tox -e core-py39,flake8

You can build the docs.  They are created in the ``docs/build`` directory:

.. code-block:: bash

    tox -e docs

You can run specific tests using pytest's options, e.g., to try one specific test:

.. code-block:: bash

    tox -e core-py39 -- -k testFromTiffRGBJPEG


Development Environment
-----------------------

To set up a development environment, you can use tox.  Use the ``core`` environment instead of the ``test`` environment if you aren't using Girder.  This is not required to run tests:

.. code-block:: bash

   tox --devenv /my/env/path -e test

and then switch to that environment:

.. code-block:: bash

   . /my/env/path/bin/activate

If you are using Girder, build and start it:

.. code-block:: bash

   girder build --dev
   girder serve
