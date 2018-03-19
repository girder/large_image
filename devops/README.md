# Large Image DevOps Tools 

Large image provides several tools for easing the provisioning of a basic system setup in different target environments. It relies on two primary tools for building system templates (e.g docker images, Amazong AMI, etc): [Packer](https://www.packer.io/) and [Ansible](http://docs.ansible.com/ansible/latest/index.html). The ansible scripts in the ```ansible``` directory are designed to take a stock Ubuntu 16.04 system and install the nessisary system libraries and python packages to run Girder with Large Image. Packer is used to bring up an Ubuntu 16.04 system in a target environment,  provision the system using the Ansible scripts,  snapshot the provisioned system,  and tear down any left over resources. The output of the Packer + Ansible process is the "snapshot"  which may be a Docker image, or something like an Amazon AWS AMI,  or a VirtualBox iso. Currently the packer scripts included with Large Image only provision a Docker image.


# Building the Docker Image

First install packer,  either through your system package manager or via packer's [download](https://www.packer.io/downloads.html) page. Next make sure you have [ansible installed](http://docs.ansible.com/ansible/latest/intro_installation.html) on your system. Then, from a checked out copy of this repository:

```sh
$> cd devops/packer
$> packer build large_image.json
```

This will pull/spin up an ubuntu 16.04 docker container,  run the playbook at ```devops/ansible/girder.yml``` against that container,  export the running container to a new system image and tag that image ```large_image/large_image:latest```.

## Note on tile sources

By default this will build Girder + Large Image with Ubuntu's default libtiff. This will support PNG and some (though not all) TIFF types.  It is possible to include additional tile sources by using the packer ```tile_sources``` variable. The available tile sources are ```mapnik``` and ```openslide```.  Both may be installed setting ```tile_sources``` to a comma separated list:

```sh
$> packer build -var "tile_sources=openslide,mapnik" large_image.json
```

_Note: that there can be no space between the commas in the list_

## Optional Variables

Several variables are available to optionally change the tagging behavior of the final image that is created

+ **docker_repo** - Set the repository of the final image (default: ```large_image/large_image```)
+ **docker_tag** - Set the tag of the final image (default: ```latest```)

For example:

```sh
$> packer build -var "docker_repo=girder/large_image" -var "docker_tag=development" large_image.json
```

Will produce a final image on your local system tagged ```girder/large_image:development```
