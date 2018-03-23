# Large Image DevOps Tools 

Large image provides several tools for easing the provisioning of a basic system setup in different target environments. It relies on two primary tools for building system templates (e.g docker images, Amazon AMI, etc): [Packer](https://www.packer.io/) and [Ansible](http://docs.ansible.com/ansible/latest/index.html). The ansible scripts in the ```ansible``` directory are designed to take a stock Ubuntu 16.04 system and install the necessary system libraries and python packages to run Girder with Large Image. 

Packer is used to bring up an Ubuntu 16.04 system in a target environment,  provision the system using the Ansible scripts,  snapshot the provisioned system,  and tear down any left over resources. The output of the Packer + Ansible process is the "snapshot"  which may be a Docker image, or something like an Amazon AWS AMI,  or a VirtualBox iso. Currently the packer scripts included with Large Image support creating Docker and Vagrantbox snapshots.


# Building the Docker Image

First install packer,  either through your system package manager or via packer's [download](https://www.packer.io/downloads.html) page. Next make sure you have [ansible installed](http://docs.ansible.com/ansible/latest/intro_installation.html) on your system. Then, from a checked out copy of this repository:

```sh
$> cd devops/packer
$> packer build docker.json
```

This will pull/spin up an ubuntu 16.04 docker container,  run the playbooks at ```devops/ansible/setup.yml```, then ```devops/ansible/girder.yml``` against that container,  export the running container to a new system image and tag that image ```large_image/large_image:latest```.


## Optional Variables

Several variables are available to optionally change the tagging behavior of the final image that is created

+ **docker_repo** - Set the repository of the final image (default: ```large_image/large_image```)
+ **docker_tag** - Set the tag of the final image (default: ```latest```)

For example:

```sh
$> packer build \
  -var "docker_repo=girder/large_image" \
  -var "docker_tag=development" \
  docker.json
  
```

Will produce a final image on your local system tagged ```girder/large_image:development```


# Building the Vagrant Box

Make sure packer is installed,  then from a checked out copy of this repository:

```sh
$> cd devops/packer
$> packer build vagrant.json
```

This will download and cache an ubuntu-16.04 iso,  run an empty VirtualBox machine,  and then install the ISO on the machine. Once the machine is up it runs the playbooks at ```devops/ansible/setup.yml```, then ```devops/ansible/girder.yml```, then ```devops/ansible/mongo.yml```  against the VM. Finally it converts the VirtualBox VM into a vagrant box file. By default this will be at ```devops/packer/builds/large_image.box```



## Optional Variables

Several variables are supported to modify aspects of the final vagrant box:

+ **vbox_memory** - The default size of the virtualbox RAM (default 1024mb)
+ **vbox_cpus** - The default number of virtualbox CPUs (default: 1)
+ **vbox_disk_size** - The size of the virtualbox disk (default: 65536 Mb)
+ **vagrant_box_name** - The name of the box file that is produced (default: ```large_image.box```)


For example:

```sh
packer build \
  -var "vbox_memory=8196" \
  -var "vbox_cpus=8" \  
  -var "vbox_disk_size=10240" \
  -var "vagrant_box_name=custom.box" \
  vagrant.json

```

Will produce a final vagrant box with 100Gb of disk space, 8Gb of RAM, 8 CPUs and save the box file to ```devops/packer/builds/custom.box```

## Notes on vagrant build

Building the Vagrant box starts by building the VirtualBox.  Here we use the ```virtualbox-iso``` builder that builds directly from an ISO.  this is slightly more complicated than the ```virtualbox-ovf``` builder that packer provides,  but ultimately much more flexible. Documentation is somewhat scarce on the vary particular requirements of things like the ```boot_command``` and ```http/pressed.cfg```. The best resource is to look at the [chef/bento](https://github.com/chef/bento) project which contains *many* working examples of deploying various operating systems. 


# Note on tile sources

By default this will build Girder + Large Image with Ubuntu's default libtiff. This will support PNG and some (though not all) TIFF types.  It is possible to include additional tile sources by using the packer ```tile_sources``` variable. The available tile sources are ```mapnik``` and ```openslide```.  Both may be installed setting ```tile_sources``` to a comma separated list:

```sh
# tile_sources also works with vagrant.json
$> packer build -var "tile_sources=openslide,mapnik" docker.json
```

_Note: that there can be no space between the commas in the list_


# Tips and Tricks

By default packer will color all output related to a particular builder. This is in case you have multiple builders defined in a single file. In this repository we define a single file for each builder and so this coloring can make it difficult to pick out problems with the provisioning scripts. It is possible to force ansible's colors to be used instead of packer like so:

```sh
ANSIBLE_FORCE_COLOR=1 packer build -color=false docker.json
```
