# Hypervisor-builder: KubeVirt

Hyperivosr-builder tool supports the kubeVirt hypervisor by kubevirt API
interfaces following the doc:
[KubeVirt API Reference](http://kubevirt.io/api-reference/)

Provide functions:
- Collect kubevirt node information
- Collect kubevirt guest information
- Guest search/start/stop

## Install Environment

Build the kubevirt hypervisor environment

## Usages

```python
from hypervisor.virt.kubevirt.kubevirtapi import KubevirtApi

def test_kubevirt():
    # set up the values
    endpoint = ''
    token = ''
    guest_name = ''
    guest_port = ''
    internal_debug = True

    # Instantiate PowerCLI object
    api = KubevirtApi(endpoint, token, internal_debug)

    # Get the VMHost information
    api.get_nodes_list()

    # Get the VM information
    vms = api.get_vms()
    vm_info = api.get_vm_info(guest_name)

    # Search the specific guest
    msgs = api.guest_search(guest_name, guest_port)

    # Power on virtual machines.
    cli.guest_start(guest_name)

    # Power off virtual machines.
    cli.guest_stop(guest_name)
```
