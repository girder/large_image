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

|         parameter        | required |                  default                  |            comments            |
|:------------------------:|:--------:|:-----------------------------------------:|:------------------------------:|
|      large_image_url     |    no    | https://github.com/girder/large_image.git |       Url to large image       |
|  large_image_virtualenv  |    yes   |                    none                   |      Path to a virtualenv      |
| large_image_tile_sources |    no    |                   [pil]                   |      List of tile sources      |
| large_image_include_vips |    no    |                   false                   | Whether to include vips or not |
|    large_image_version   |    no    |                   master                  |     Version of large_image     |

* pil, tiff, svs and mapnik are possible large_image_tile_sources

Dependencies
--------------

None.

Generated Facts
---------------

|     parameter    |     value     |     description     |
|:----------------:|:-------------:|:-------------------:|
| large_image_path | ~/large_image | Path to large image |


Example Playbook
------------------

Here is a playbook which installs svs and tiff tile sources
and includes vips so that we can run conversion tasks with girder_worker.

	---

	- hosts: servers
	  tasks:
	  - include_role:
		  name: large_image
		  vars:
			large_image_virtualenv: "/path/to/a/virtualenv"
			large_image_tile_sources:
			  - svs
			  - tiff
			large_image_include_vips: true
	  ...
