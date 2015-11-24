# Vagrant

A remarkably easy way of quickly installing and using `TSTools` is to utilize the included setup script for the [Vagrant](https://www.vagrantup.com/) technology. [Vagrant](https://www.vagrantup.com/) enables users to quickly and reproducibly configure and create lightweight virtual machines. I have included a `Vagrantfile` inside `vagrant/` that sets up a Ubuntu "Trusty" 14.04 Linux virtual machine with TSTools and all pre-requisites installed.

To run TSTools using Vagrant, install Vagrant for your platform from [their downloads page](http://www.vagrantup.com/downloads):

http://www.vagrantup.com/downloads

Installation instructions are [available here](https://docs.vagrantup.com/v2/installation/index.html).

You will also need software to run the virtual machine, or a "provider" as Vagrant calls it. I recommend [VirtualBox](https://www.virtualbox.org/wiki/Downloads) because it works well, is cross-platform, and is free and open-source. More providers and instructions for using these providers is available [on Vagrant's documentation page](https://docs.vagrantup.com/v2/providers/index.html).

Once you have Vagrant and a provider installed, you can run the Vagrant machine as follows:

``` bash
# Navigate into the folder and vagrant up!
cd vagrant/
vagrant up
```

Once the virtual machine has been downloaded, configured, and provisioned, you can connect to it and launch QGIS via SSH:

``` bash
vagrant ssh
qgis
```

That's it! You can `suspend`, `halt`, or `destroy` (delete) the virtual machine when you're done using these as the `<command>` in `vagrant <command>`.

For more information about Vagrant and how to use the technology, check out their ["Getting Started"](https://docs.vagrantup.com/v2/getting-started/index.html) section within [their documentation page](https://docs.vagrantup.com/v2/).
