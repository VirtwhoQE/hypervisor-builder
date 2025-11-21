from setuptools import setup

setup(
    name="hypervisor-builder",
    version="0.1",
    packages=[
        "hypervisor",
        "hypervisor.virt",
        "hypervisor.virt.ahv",
        "hypervisor.virt.esx",
        "hypervisor.virt.xen",
        "hypervisor.virt.rhevm",
        "hypervisor.virt.hyperv",
        "hypervisor.virt.libvirt",
        "hypervisor.virt.kubevirt",
    ],
    url="https://github.com/VirtwhoQE/hypervisor-builder",
    license="GPL-3.0",
    author="",
    author_email="",
    description="Library to set up various hypervisors for virt-who testing.",
)
