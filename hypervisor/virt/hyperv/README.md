# Hypervisor-builder: Hyper-V
Hyperivosr-builder tool supports the Hyper-V hypervisor by PowerCLI Commands


Provide functions:
- Collect vcenter information  
- Host uuid
- Guest search/add/delete/start/stop/suspend/resume  


## Install Environment
Set up the Hyper-V environment


## Usages
```
from hypervisor.virt.hyperv.hypervcli import HypervCLI


def test_hypervcli():
    # set up the values
    server = ''
    ssh_user = ''
    ssh_passwd = ''
    guest_name = ''
    image_path = ''

    # Instantiate HypervCLI object
    cli = HypervCLI(server, ssh_user, ssh_passwd)

    # Get the VMHost information
    cli.info()

    # Search the specific guest
    msgs = cli.guest_search(guest_name)

    # Create a new virtual machine.
    cli.guest_add(guest_name, image_path)
    
    # Remove the specified virtual machines from Hyper-v hypervisor.
    cli.guest_del(guest_name)
    
    # Check if the Hyper-v guest exists
    cli.guest_exist(guest_name)
    
    # Power on virtual machines.
    cli.guest_start(guest_name)
    
    # Power off virtual machines.
    cli.guest_stop(guest_name)
    
    # Suspend virtual machines.
    cli.guest_suspend(guest_name)
    
    # Resume virtual machines
    cli.guest_resume(guest_name)
```
