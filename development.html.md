# Developer Guide

## Developer Installation

To install all packages from source, clone the repository:

```default
git clone https://github.com/girder/large_image.git
cd large_image
```

Install all packages and dependencies:

```default
pip install -e . -r requirements-dev.txt
```

If you aren’t developing with Girder 3, you can skip installing those components.  Use `requirements-dev-core.txt` instead of `requirements-dev.txt`:

```default
pip install -e . -r requirements-dev-core.txt
```

### Tile Source Requirements

Many tile sources have complex prerequisites.  These can be installed directly using your system’s package manager or from some prebuilt Python wheels for Linux.  The prebuilt wheels are not official packages, but they can be used by instructing pip to use them by preference:

```default
pip install -e . -r requirements-dev.txt --find-links https://girder.github.io/large_image_wheels
```

### Test Requirements

Besides an appropriate version of Python, Large Image tests are run via [tox](https://tox.readthedocs.io/en/latest/).  This is also a convenient way to setup a development environment.

The `tox` Python package must be installed:

```bash
pip install tox
```

See the tox documentation for how to recreate test environments or perform other maintenance tasks.

By default, instead of storing test environments in a `.tox` directory, they are stored in the `build/tox` directory.  This is done for convenience in handling build artifacts from Girder-specific tests.

### nodejs and npm for Girder Tests or Development

`nodejs` version 14.x and a corresponding version of `npm` are required to build and test Girder client code.  See [nodejs](https://nodejs.org/en/download/) for how to download and install it.  Remember to get version 12 or 14.

### Mongo for Girder Tests or Development

To run the full test suite, including Girder, ensure that a MongoDB instance is ready on `localhost:27017`.  This can be done with docker via `docker run -p 27017:27017 -d mongo:latest`.

## Running Tests

Tests are run via tox environments:

```bash
tox -e test-py39,lint,lintclient
```

Or, without Girder:

```bash
tox -e core-py39,lint
```

You can build the docs.  They are created in the `docs/build` directory:

```bash
tox -e docs
```

You can run specific tests using pytest’s options, e.g., to try one specific test:

```bash
tox -e core-py39 -- -k testFromTiffRGBJPEG
```

## Development Environment

To set up a development environment, you can use tox.  This is not required to run tests.  The `dev` environment allows for complete use.  The `test` environment will also install pytest and other tools needed for testing.  Use the `core` environment instead of the `dev` environment if you aren’t using Girder.

For OSX users, specify the `dev-osx` environment instead; it will install only the cross-platform common sources.

You can add a suffix to the environment to get a specific version of python (e.g., `dev-py311` or `dev-osx-py310`.

```bash
tox --devenv /my/env/path -e dev
```

and then switch to that environment:

```bash
. /my/env/path/bin/activate
```

If you are using Girder, build and start it:

```bash
girder build --dev
girder serve
```
