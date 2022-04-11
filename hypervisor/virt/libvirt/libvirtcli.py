import re

from hypervisor import FailException
from hypervisor import logger
from hypervisor.ssh import SSHConnect


class LibvirtCLI:
    def __init__(self, server, ssh_user, ssh_passwd):
        """
        Collect libvirt information, provide Host add/delete and
        Guest add/delete/start/stop/suspend/resume functions
        via virsh Command line
        :param server: the ip for the libvirt server
        :param ssh_user: the ssh user for the libvirt server
        :param ssh_passwd: the ssh password for the libvirt server
        """
        self.server = server
        self.ssh_user = ssh_user
        self.ssh_passwd = ssh_passwd
        self.ssh = SSHConnect(self.server, user=self.ssh_user, pwd=self.ssh_passwd)

    def host_uuid(self):
        """
        Get uuid for libvirt host
        :return: uuid for libvirt host
        """
        cmd = "virsh capabilities |grep '<uuid>'"
        ret, output = self.ssh.runcmd(cmd)
        if not ret and "uuid" in output:
            uuid = re.findall(r"<uuid>(.*?)</uuid>", output)[-1].strip()
            logger.info("Succeeded to get libvirt host({0}) uuid is: {1}".format(self.server, uuid))
            return uuid
        else:
            raise FailException("Failed to check libvirt host({0}) uuid".format(self.server))

    def guest_exist(self, guest_name):
        """
        Check if the esx guest exists
        :param guest_name: the name for the guest
        :return: guest exists, return True, else, return False.
        """
        cmd = "virsh  dominfo {0} | grep '^Name'".format(guest_name)
        ret, output = self.ssh.runcmd(cmd)
        if not ret and guest_name in output:
            logger.info("libvirt({0}) guest {1} is exist".format(self.server, guest_name))
            return True
        else:
            logger.info("libvirt({0}) guest {1} is not exist".format(self.server, guest_name))
            return False

    def guest_uuid(self, guest_name):
        """
        Get uuid for libvirt guest
        :param guest_name: the guest name for libvirt guest
        :return: uuid for libvirt guest
        """
        cmd = "virsh domuuid {0}".format(guest_name)
        ret, output = self.ssh.runcmd(cmd)
        if not ret and output is not None:
            uuid = output.strip()
            logger.info("Succeeded to get libvirt({0}) guest uuid: {1}".format(self.server, uuid))
            return uuid
        else:
            logger.info("Failed to check libvirt({0}) guest uuid".format(self.server))

    def guest_status(self, guest_name):
        """
        Get the status for the guest
        :param guest_name: name for the specific guest
        :return: the status for the guest
        """
        cmd = "virsh  domstate {0}".format(guest_name)
        ret, output = self.ssh.runcmd(cmd,)
        if not ret and output.strip() is not None and output.strip() !="":
            status = output.strip()
            logger.info("libvirt({0}) guest status is: {1}".format(self.server, status))
            return status
        else:
            logger.info("Failed to check libvirt({0}) guest status".format(self.server))
            return "false"

    def guest_mac(self, guest_name):
        """
        Get the mac address for the guest
        :param guest_name: name for the specific guest
        :return: the mac address for the guest
        """
        cmd = "virsh dumpxml {0} | grep 'mac address'".format(guest_name)
        ret, output = self.ssh.runcmd(cmd)
        if not ret:
            mac_addr = re.findall(r"mac address='(.*?)'", output)[0]
            if mac_addr is not None or mac_addr != "":
                logger.info("Succeeded to get libvirt({0}) guest mac: {1}".format(self.server, mac_addr))
                return mac_addr
        raise FailException("Failed to get libvirt({0}) guest mac address".format(self.server))

    def guest_ip(self, guest_name):
        """
        Get guest ip by mac
        :param guest_name: name for the specific guest
        :return:
        """
        gateway = self.get_gateway(self.server)
        guest_mac = self.get_guest_mac(guest_name)
        option = "grep 'Nmap scan report for' | grep -Eo '([0-9]{1,3}[\.]){3}[0-9]{1,3}'| tail -1"
        cmd = f"nmap -sP -n {gateway} | grep -i -B 2 {guest_mac} | {option}"
        guest_ip = self.ssh.runcmd(cmd)
        if guest_ip is not False and guest_ip is not None and guest_ip != "":
            return guest_ip
        else:
            logger.info(f"Failed to get libvirt guest ip")

    def get_gateway(self, host_ip):
        """
        Get the gateway by ip route command
        :param host_ip: the ip for the libvirt host
        :param host_user: the ssh username for the libvirt host
        :param host_pwd: the ssh password for the libvirt host
        :return: the gateway for host
        """
        cmd = f"ip route | grep {host_ip}"
        ret, output = self.ssh.runcmd(cmd)
        if not ret and output is not None and output is not "":
            output = output.strip().split(" ")
            if len(output) > 0:
                gateway = output[0]
                return gateway
        raise FailException(f"Failed to get gateway({host_ip})")

    def get_guest_mac(self, guest_name):
        """
        Get the mac address for the guest
        :param guest_name: name for the specific guest
        :return: the mac address for the guest
        """
        cmd = "virsh dumpxml {0} | grep 'mac address'".format(guest_name)
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0:
            mac_addr = re.findall(r"mac address='(.*?)'", output)[0]
            if mac_addr is not None or mac_addr != "":
                logger.info("Succeeded to get libvirt({0}) guest mac: {1}".format(self.server, mac_addr))
                return mac_addr
        raise FailException("Failed to get libvirt({0}) guest mac address".format(self.server))

    def guest_start(self, guest_name):
        """
        Power on virtual machines.
        :param guest_name: the virtual machines you want to power on.
        :return: power on successfully, return True, else, return False.

        """
        cmd = "virsh --connect qemu:///system start {0}".format(guest_name)
        ret, output = self.ssh.runcmd(cmd)
        if "Failed to connect socket to '/var/run/libvirt/virtlogd-sock'" in output:
            cmd = "systemctl start virtlogd.socket"
            self.ssh.runcmd(cmd)
            cmd = "virsh --connect qemu:///system start {0}".format(guest_name)
            self.ssh.runcmd(cmd)
        if self.guest_status(guest_name) is 'running':
            logger.info(
                "Succeeded to start libvirt({0}) guest".format(self.server))
            return True
        else:
            logger.info("Failed to start libvirt({0}) guest".format(self.server))
            return False

    def guest_stop(self, guest_name):
        """
        Power off virtual machines.
        :param guest_name: the virtual machines you want to power off.
        :return: stop successfully, return True, else, return False.
        """
        cmd = "virsh shutdown {0}".format(guest_name)
        ret, output = self.ssh.runcmd(cmd)
        if not ret and self.guest_status(guest_name) == "shut off":
            logger.info("Succeeded to shutdown libvirt({0}) guest".format(self.server))
            return True
        else:
            logger.info("Failed to shutdown libvirt({0}) guest".format(self.server))
            return False

    def guest_suspend(self, guest_name):
        """
        Suspend virtual machines.
        :param guest_name: the virtual machines you want to suspend.
        :return: suspend successfully, return True, else, return False.
        """
        cmd = "virsh suspend {0}".format(guest_name)
        ret, output = self.ssh.runcmd(cmd)
        if not ret and self.guest_status(guest_name) == "paused":
                logger.info("Succeeded to pause libvirt({0}) guest".format(self.server))
                return True
        else:
            logger.info("Failed to pause libvirt({0}) guest".format(self.server))
            return False

    def guest_resume(self, guest_name):
        """
        Resume virtual machines.
        :param guest_name: the virtual machines you want to resume.
        :return: resume successfully, return True, else, return False.
        """
        cmd = "virsh resume {0}".format(guest_name)
        ret, output = self.ssh.runcmd(cmd)
        if not ret and self.guest_status(guest_name) == "running":
            logger.info("Succeeded to resume libvirt({0}) guest".format(self.server))
            return True
        else:
            logger.info("Failed to resume libvirt({0}) guest".format(self.server))
            return False