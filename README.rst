hypervisor-builder is a tool to check hyperivsor's informaiton, manage virtual machines by different cli or api.

These hypervisors will be supported:

[Vcenter]
    - Connection 
        + Powercli Command line (Default)
        + Suds with wsdl
    - Collect vcenter information
    - Host add/delete
    - Guest add/delete/start/stop/suspend/resume

[Hyper-V]
    - Connection
        + Powershell Command line (Default)
        + NTLM authentication
    - Collect hyperv information
    - Guest add/delete/start/stop/suspend/resume

[RHEVM]
    - Connection
        + ovirt-shell command line(Default)
        + API
    - Collect rhevm information
    - Guest add/delete/start/stop/suspend/resume

[Libvirt]
    - Connection
        + virsh command line
    - Collect libvirt information
    - Guest add/delete/start/stop/suspend/resume

[XEN]
    - Connection
        + xe command line
    - Collect xen information
    - Guest add/delete/start/stop/suspend/resume

[Kubevirt]
    - Connection
        + API
    - Collect kubevirt information
    - Guest add/delete/start/stop/suspend/resume
