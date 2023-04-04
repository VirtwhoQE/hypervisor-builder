from hypervisor import FailException
from hypervisor import logger
from hypervisor.ssh import SSHConnect

import time
import random


class RHEVMCLI:
    def __init__(self, server, ssh_user, ssh_pwd, *admin_option):
        """
        Collect RHEVM information, provide Guest add/delete/start/stop/suspend/resume functions
        via ovirt-shell Command line following 'https://access.redhat.com/documentation/en-us/
        red_hat_virtualization/4.1/html-single/rhevm_shell_guide/index'
        :param server: the ip for the RHEVM server
        :param ssh_user: the ssh user for the RHEVM server
        :param ssh_pwd: the ssh password for the RHEVM server
        """
        self.server = server
        self.ssh_user = ssh_user
        self.ssh_pwd = ssh_pwd
        self.ssh = SSHConnect(self.server, user=self.ssh_user, pwd=self.ssh_pwd)
        if not self.shell_connection():
            self.shell_config(*admin_option)

    def url(self):
        """
        Get the URL to the Red Hat Virtualization Manager's REST API.
        This takes the form of https://[server]/ovirt-engine/api.
        :return:
        """
        ret, output = self.ssh.runcmd("hostname")
        if not ret and output is not None and output is not "":
            hostname = output.strip()
            return f"https://{hostname}:443/ovirt-engine"
        else:
            raise FailException(f"Failed to get url for RHEVM {self.server}")

    def random_mac(self):
        """
        Generate the mac address randomly.
        :return: mac address
        """
        mac = [
            0x06,
            random.randint(0x00, 0x2F),
            random.randint(0x00, 0x3F),
            random.randint(0x00, 0x4F),
            random.randint(0x00, 0x8F),
            random.randint(0x00, 0xFF),
        ]
        return ":".join(map(lambda x: "%02x" % x, mac))

    def shell_connection(self):
        """
        Check if the oVirt manager could be reached.
        :return:
        """
        cmd = f"echo | ovirt-shell -c -E  'ping'"
        ret, output = self.ssh.runcmd(cmd)
        if not ret and "success" in output:
            logger.info(f"Succeeded to connect RHEVM({self.server}) shell")
            return True
        else:
            logger.info(f"Failed to connect RHEVM({self.server}) shell")
            return False

    def shell_config(self, admin_user, admin_pwd):
        """
        The URL, user name, certificate authority file, and password for connecting to the RHEVM
        can be configured in the .ovirtshellrc file. Config the RHEVM shell.
        :param admin_user: The user name and directory service domain of the user attempting
        access to the RHEVM. This takes the form of [username]@[domain].
        :param admin_pwd: The password for the user attempting access to the RHEVM.
        :return:
        """
        api_url = f"{self.url()}/api"
        ca_file = "/etc/pki/ovirt-engine/ca.pem"
        options = (
            "insecure = False\n" "no_paging = False\n" "filter = False\n" "timeout = -1"
        )
        rhevm_shellrc = "/root/.ovirtshellrc"
        cmd = (
            f"echo -e '[ovirt-shell]\n"
            f"username = {admin_user}\n"
            f"password = {admin_pwd}\n"
            f"ca_file = {ca_file}\n"
            f"url = {api_url}\n"
            f"{options}' > {rhevm_shellrc}"
        )
        self.ssh.runcmd(cmd)
        self.ssh.runcmd("ovirt-aaa-jdbc-tool user unlock admin")

    def info(self):
        """
        Get the VMhost info
        :return: the VMHosts info
        """
        cmd = "ovirt-shell -c -E 'list hosts' | grep '^name' | awk -F ':' '{print $2}'"
        ret, output = self.ssh.runcmd(cmd)
        if not ret and output is not None and output is not "":
            hosts = output.strip().split("\n")
        else:
            hosts = list()
        logger.info(f"Get RHEVM Host: {hosts}")
        return hosts

    def guest_search(self, guest_name, host_ip, host_user, host_pwd):
        """
        Search the specific guest, return the expected attributes
        :param guest_name: name for the specific guest
        :param host_ip: the ip for the RHEVM host
        :param host_user: the ssh username for the RHEVM host
        :param host_pwd: the ssh password for the RHEVM host
        :return: guest attributes, exclude guest_name, guest_ip, guest_uuid ...
        """
        host_id = self.get_rhevm_info("vm", guest_name, "host-id")
        cluster_id = self.get_rhevm_info("vm", guest_name, "cluster-id")
        guest_msgs = {
            "guest_name": guest_name,
            "guest_ip": self.get_guest_ip(guest_name, host_ip, host_user, host_pwd),
            "guest_uuid": self.get_rhevm_info("vm", guest_name, "id"),
            "guest_state": self.get_rhevm_info("vm", guest_name, "status-state"),
            "vdsm_uuid": host_id,
            "vdsm_hwuuid": self.get_rhevm_info(
                "host", host_id, "hardware_information-uuid"
            ),
            "vdsm_hostname": self.get_rhevm_info("host", host_id, "name"),
            "vdsm_version": self.get_rhevm_info(
                "host", host_id, "version-full_version"
            ),
            "vdsm_cpu": self.get_rhevm_info("host", host_id, "cpu-topology-sockets"),
            "vdsm_cluster": self.get_rhevm_info("cluster", cluster_id, "name"),
        }
        return guest_msgs

    def get_rhevm_info(self, object_type, object_id, value):
        """
        Get the info from RHEVM
        :param object_type: The type of object to retrieve, such as vm, host, cluster and so on.
        :param object_id:  <id|name> The object identifier or the object identifier
        :param value: the value you want to get from the result
        :return: the value you want to get
        """
        cmd = f"ovirt-shell -c -E 'show {object_type} {object_id}' |grep '^{value}'"
        ret, output = self.ssh.runcmd(cmd)
        if not ret and value in output:
            result = output.strip().split(":")[1].strip()
            logger.info(
                f"Succeeded to get rhevm {object_type} ({object_id}) {value}: {result}"
            )
            return result
        else:
            logger.info(f"Failed to get rhevm {object_type} ({object_id}) {value}")
            return None

    def get_guest_ip(self, guest_name, host_ip, host_user, host_pwd):
        """
        Get guest ip by mac
        :param guest_name: name for the specific guest
        :param host_ip: the ip for the RHEVM host
        :param host_user: the ssh username for the RHEVM host
        :param host_pwd: the ssh password for the RHEVM host
        :return:
        """
        gateway = self.get_gateway(host_ip, host_user, host_pwd)
        guest_mac = self.get_guest_mac(guest_name)
        option = "grep 'Nmap scan report for' | grep -Eo '([0-9]{1,3}[\.]){3}[0-9]{1,3}'| tail -1"
        cmd = f"nmap -sP -n {gateway} | grep -i -B 2 {guest_mac} | {option}"
        ret, output = SSHConnect(host_ip, host_user, host_pwd).runcmd(cmd)
        if not ret and output is not None and output is not "":
            guest_ip = output.strip()
            logger.info(f"Succeeded to get rhevm guest ip ({guest_ip})")
            return output.strip()
        else:
            logger.info(f"Failed to get rhevm guest ip")

    def get_gateway(self, host_ip, host_user, host_pwd):
        """
        Get the gateway by ip route command
        :param host_ip: the ip for the RHEVM host
        :param host_user: the ssh username for the RHEVM host
        :param host_pwd: the ssh password for the RHEVM host
        :return: the gateway for host
        """
        cmd = f"ip route | grep {host_ip}"
        ret, output = SSHConnect(host_ip, host_user, host_pwd).runcmd(cmd)
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
        cmd = f"ovirt-shell -c -E 'list nics --parent-vm-name {guest_name} --show-all' | grep  '^mac-address'"
        ret, output = self.ssh.runcmd(cmd)
        if not ret and "mac-address" in output:
            mac_addr = output.strip().split(": ")[1].strip()
            logger.info(f"rhevm({self.server}) guest mac is: {mac_addr}")
            return mac_addr
        else:
            logger.info(f"Failed to check rhevm({self.server}) guest mac")
            return None

    def guest_disk_uuid(self, guest_name):
        """
        Get the uuid of the disk
        :param guest_name: the name of the guest
        :return: the uuid of the disk
        """
        vm_options = "--parent-vm-name {0}".format(guest_name)
        cmd = f"ovirt-shell -c -E 'list disks {vm_options}' | grep '^id'"
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and "id" in output:
            uuid = output.strip().split(":")[1].strip()
            logger.info(f"rhevm({self.server}) disk uuid for guest: {uuid}")
            return uuid
        else:
            raise FailException(
                f"Failed to check rhevm({self.server}) disk uuid for guest"
            )

    def guest_disk_ready(self, guest_name, disk):
        """
        check if the disk exist
        :param guest_name: the name of the guest
        :param disk: the name of the disk
        :return:
        """
        vm_options = "--parent-vm-name {0}".format(guest_name)
        cmd = f"ovirt-shell -c -E 'list disks {vm_options}' | grep '^name'"
        ret, output = self.ssh.runcmd(cmd)
        if ret != 0 or disk not in output:
            raise FailException(f"rhevm({self.server}) guest disk is not exist")
        disk_uuid = self.guest_disk_uuid(guest_name)
        is_actived_disk = ""
        status = ""
        for i in range(60):
            time.sleep(60)
            if self.guest_disk_is_actived(guest_name):
                is_actived_disk = "Yes"
            else:
                cmd = (
                    f"ovirt-shell -c -E 'action disk {disk_uuid} activate {vm_options}'"
                )
                self.ssh.runcmd(cmd)
            if is_actived_disk == "Yes" and self.guest_disk_status(guest_name) == "ok":
                logger.info(
                    f"rhevm({self.server}) guest disk is actived and status is ok"
                )
                status = "ok"
                break
        if is_actived_disk != "Yes" or status != "ok":
            raise FailException(
                f"Failed to create rhevm({self.server}) guest as disk can't be actived"
            )

    def guest_disk_status(self, guest_name):
        """
        Get the status for the disk
        :param guest_name:
        :return: the status for the disk
        """
        vm_options = f"--parent-vm-name {guest_name}"
        cmd = f"ovirt-shell -c -E 'list disks {vm_options} --show-all' | grep '^status-state'"
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and "status-state" in output:
            status = output.strip().split(":")[1].strip()
            logger.info(f"rhevm({self.server}) disk for guest status: {status}")
            return status
        else:
            raise FailException(
                f"Failed to check rhevm({self.server}) guest disk status"
            )

    def guest_disk_is_actived(self, guest_name):
        """
        Check if the disk is active
        :param guest_name: the name of the guest
        :return:
        """
        vm_options = f"--parent-vm-name {guest_name}"
        cmd = f"ovirt-shell -c -E 'list disks {vm_options} --show-all' | grep '^active'"
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and "True" in output:
            return True
        else:
            return False

    def guest_nic(self, guest_name):
        """
        get the nic of the guest
        :param guest_name:
        :return:
        """
        options = f"list nics --parent-vm-name {guest_name} --show-all"
        cmd = f"ovirt-shell -c -E '{options}' | grep  '^name'"
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and "name" in output:
            nic = output.strip().split(": ")[1].strip()
            logger.info(f"rhevm({self.server}) guest nic is: {nic}")
            return nic
        else:
            raise FailException(f"Failed to check rhevm({self.server}) guest nic")

    def guest_add(self, guest_name, template, cluster, disk, host_name=None):
        """
        Create a new virtual machine.
        Note: You should prepare a rhevm template at first.(Please refer to
        'https://access.redhat.com/documentation/en-us/red_hat_virtualization/4.1/html/
        virtual_machine_management_guide/creating_a_template_from_an_existing_virtual_machine')
        :param guest_name: the name for the new virtual machine
        :param template: the name of the template
        :param cluster: the name of the cluster
        :param disk: the name of the disk
        :param host_name: the name of the rhevm host
        :return:
        """
        if not host_name:
            host_name = self.info()[0]
        if self.guest_exist(guest_name):
            self.guest_del(guest_name)
        cmd = (
            f"ovirt-shell -c -E 'add vm "
            f"--name {guest_name} "
            f"--cluster-name {cluster} "
            f"--template-name {template} "
            f"--placement_policy-host-name {host_name}'"
        )
        self.ssh.runcmd(cmd)
        guest_uuid = self.get_rhevm_info("vm", guest_name, "id")
        guest_nic = self.guest_nic(guest_name)
        guest_mac = self.random_mac()
        vm_options = f"--parent-vm-identifier {guest_uuid}"
        cmd = f"ovirt-shell -c -E 'update nic {guest_nic} {vm_options} --mac-address {guest_mac}'"
        self.ssh.runcmd(cmd)
        logger.info(f"rhevm({self.server}) guest new mac is: {guest_mac}")
        self.guest_disk_ready(guest_name, disk)
        self.guest_start(guest_name)

    def guest_del(self, guest_name):
        """
        Remove the specified virtual machines from the vCenter Server system.
        :param guest_name: the virtual machines you want to remove.
        :return: remove successfully, return True, else, return False.
        """
        if self.guest_exist(guest_name):
            self.guest_stop(guest_name)
            cmd = f"ovirt-shell -c -E 'remove vm {guest_name} --vm-disks-detach_only'"
            ret, _ = self.ssh.runcmd(cmd)
            if not ret and self.guest_exist(guest_name) is False:
                logger.info(f"Succeeded to delete rhevm({self.server}) guest")
                return True
            else:
                logger.info(f"Failed to delete rhevm({self.server}) guest")
                return False

    def guest_exist(self, guest_name):
        """
        Check if the esx guest exists
        :param guest_name: the name for the guest
        :return: guest exists, return True, else, return False.
        """
        cmd = f"ovirt-shell -c -E 'show vm {guest_name}' |grep '^name'"
        ret, output = self.ssh.runcmd(cmd)
        if not ret and guest_name in output:
            logger.info(f"rhevm({self.server}) guest {guest_name} is exist")
            return True
        else:
            logger.info(f"rhevm({self.server}) guest {guest_name} is not exist")
            return False

    def guest_start(self, guest_name, host_name=None):
        """
        Power on virtual machines.
        :param guest_name: the virtual machines you want to power on.
        :param host_name: the name of the rhevm host
        :return: power on successfully, return True, else, return False.

        """
        if self.get_rhevm_info("vm", guest_name, "status-state") == "up":
            logger.info(f"Rhevm({self.server}) guest is in Up status")
            return True
        if not host_name:
            host_name = self.info()[0]
        cmd = f"ovirt-shell -c -E 'action vm {guest_name} start --vm-placement_policy-host-name {host_name}'"
        ret, output = self.ssh.runcmd(cmd)
        if (
            not ret
            and "ERROR" not in output
            and self.get_rhevm_info("vm", guest_name, "status-state") == "up"
        ):
            logger.info(f"Succeeded to start rhevm({self.server}) guest")
            return True
        else:
            logger.info(f"Failed to start rhevm({self.server}) guest")
            return False

    def guest_stop(self, guest_name):
        """
        Power off virtual machines.
        :param guest_name: the virtual machines you want to power off.
        :return: stop successfully, return True, else, return False.
        """
        cmd = f"ovirt-shell -c -E 'action vm {guest_name} stop'"
        ret, _ = self.ssh.runcmd(cmd)
        status = self.get_rhevm_info("vm", guest_name, "status-state")
        if not ret and status == "down":
            logger.info(f"Succeeded to stop rhevm({self.server}) guest")
            return True
        else:
            raise FailException(f"Failed to stop rhevm({self.server}) guest")

    def guest_suspend(self, guest_name):
        """
        Suspend virtual machines.
        :param guest_name: the virtual machines you want to suspend.
        :return: suspend successfully, return True, else, return False.
        """
        if self.get_rhevm_info("vm", guest_name, "status-state") == "suspended":
            logger.info(f"Rhevm({self.server}) guest is in suspended status")
            return True
        cmd = f"ovirt-shell -c -E 'action vm {guest_name} suspend'"
        ret, _ = self.ssh.runcmd(cmd)
        if (
            not ret
            and self.get_rhevm_info("vm", guest_name, "status-state") == "suspended"
        ):
            logger.info(f"Succeeded to suspend rhevm({self.server}) guest")
            return True
        else:
            logger.info(f"Failed to suspend rhevm({self.server}) guest")
            return False
