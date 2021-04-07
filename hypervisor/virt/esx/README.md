# Hypervisor-builder: vCenter
Hyperivosr-builder tool supports the vcenter hypervisor by PowerCLI Commands following the doc:  
[VMware vSphere PowerCLI Cmdlets Reference](https://vdc-repo.vmware.com/vmwb-repository/dcr-public/f2319b2a-6378-4635-a1cd-90b14949b62a/0ac4f829-f79b-40a6-ac10-d22ec76937ec/doc/index.html)


Provide functions:
- Collect vcenter information  
- Host search/add/delete/restart/start/stop
- Guest search/add/delete/start/stop/suspend/resume  


## Install Environment
Build the vcenter and ESXi host environment


## Usages
```
from hypervisor.virt.esx.powercli import PowerCLI


def test_powercli():
    # set up the values
    server = ''
    admin_user = ''
    admin_passwd = ''
    ssh_user = ''
    ssh_passwd = ''
    guest_name = ''
    esx_host = ''
    esx_host_user = ''
    esx_host_pwd = ''
    image_path = ''

    # Instantiate PowerCLI object
    cli = PowerCLI(server, admin_user, admin_passwd, ssh_user, ssh_passwd)

    # Get the VMHost information
    cli.info()

    # Search the specific guest
    msgs = cli.guest_search(guest_name)
    
    # Add a host to be managed by a vCenter Server system.
    cli.host_add("DC-cluster", esx_host, esx_host_user, esx_host_pwd)
    
    # Remove the specified hosts from the inventory.
    cli.host_del(esx_host)
    
    # Check if the esx host exists
    cli.host_exist(esx_host)
    
    # Restart the specified host.
    cli.host_restart(esx_host)
    
    # Search the specific host
    cli.host_search(esx_host)
    
    # Modify the configuration of the host.
    cli.host_set(esx_host, 'Connected')
    
    # Start the specified hosts.
    cli.host_start(esx_host)
    
    # Power off the specified hosts.
    cli.host_stop(esx_host)

    # Create a new virtual machine.
    cli.guest_add(esx_host, esx_host_user, esx_host_pwd, guest_name, image_path)
    
    # Remove the specified virtual machines from the vCenter Server system.
    cli.guest_del(guest_name)
    
    # Check if the esx guest exists
    cli.guest_exist(guest_name)
    
    # Power on virtual machines.
    cli.guest_start(guest_name)
    
    # Power off virtual machines.
    cli.guest_stop(guest_name)
    
    # Suspend virtual machines.
    cli.guest_suspend(guest_name)
```
