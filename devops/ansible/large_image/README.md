girder.large_image
==========================

An ansible role to install large_image.

Requirements
--------------

Currently the role supports Ubuntu 16.04(xenial) and Ubuntu 18.04(bionic) and
requires a virtualenv path to be defined.

Role Variables
----------------

See the table below for a summary of variables.

|         parameter        | required | default |            comments            |
|:------------------------:|:--------:|:-------:|:------------------------------:|
|  large_image_virtualenv  |    yes   |   none  |      Path to a virtualenv      |
| large_image_tile_sources |    no    |  [pil]  |      List of tile sources      |
| large_image_include_vips |    no    |  false  | Whether to include vips or not |

#### large_image_virtualenv
This is a required variable. Provide a path to a virtual environment.

#### large_image_tile_sources
This is not a required variable. If not provided only the pil tile source will be installed.
Possible tile sources are:
  - pil
  - mapnik
  - tiff
  - svs

#### large_image_include_vips
This is not a required variable. Default behavior is not to install vips.
Vips is needed if large_image will convert files using girder_worker.

Dependencies
--------------

None.

Example Playbook
------------------

Here is a playbook which installs svs and tiff tile sources
and includes vips so that we can run conversion tasks with girder_worker.

    - hosts: server
      vars:
        - large_image_virtualenv: "/path/to/a/virtualenv"
        - large_image_tile_sources:
          - svs
          - tiff
        - large_image_include_vips: true
      roles:
         - large_image


Running Tests
---------------

We use [molecule](https://molecule.readthedocs.io/en/latest/) with [testinfra](https://testinfra.readthedocs.io/en/latest/) to test different tile sources.
In order to run a specific test scenario first install molecule.

```sh
pip install molecule
```

Then run a scenario in this directory:

```sh
molecule test -s mapnik
```

To run all the scenarios:
```sh
molecule test --all
```

For more information check [molecule's API](https://molecule.readthedocs.io/en/latest/usage.html).
