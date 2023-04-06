# Hypervisor-builder: Libvirt
Hyperivosr-builder tool supports the libvirt hypervisor by virsh Commands


Provide functions:
- Collect libvirt information
- Libvirt host uuid/version/cpu
- Guest search/start/stop/suspend/resume


## Install Environment
Set up the libvirt environment


## Usages
```
from hypervisor.virt.libvirt.libvirtcli import LibvirtCLI


def test_libevirt():
    # set up the values
    server = ''
    username = ''
    password = ''
    guest_name = ''

    # Instantiate libvirt object
    cli = LibvirtCLI(server, username, password)

    # Search the specific guest
    msgs = cli.guest_search(guest_name)
    
    # Check if the Hyper-v guest exists
    cli.guest_exist(guest_name)
    
    # Power on virtual machines.
    cli.guest_start(guest_name)
    
    # Power off virtual machines.
    cli.guest_stop(guest_name)
    
    # Suspend virtual machines.
    cli.guest_suspend(guest_name)
    
    # Resume virtual machines.
    cli.guest_resume(guest_name)
```
