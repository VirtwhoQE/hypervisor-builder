import json
import re

from hypervisor import FailException
from hypervisor import logger
from hypervisor.ssh import SSHConnect


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
        if not self.rhevm_shell_connection():
            self.rhevm_shell_config(*admin_option)

    def rhevm_url(self):
        """
        Get the URL to the Red Hat Virtualization Manager's REST API.
        This takes the form of https://[server]/ovirt-engine/api.
        :return:
        """
        ret, output = self.ssh.runcmd('hostname')
        if not ret and output is not None and output is not "":
            hostname = output.strip()
            return f"https://{hostname}:443/ovirt-engine"
        else:
            raise FailException(f"Failed to get url for RHEVM {self.server}")

    def rhevm_shell_connection(self):
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

    def rhevm_shell_config(self, admin_user, admin_pwd):
        """
        The URL, user name, certificate authority file, and password for connecting to the RHEVM
        can be configured in the .ovirtshellrc file. Config the RHEVM shell.
        :param admin_user: The user name and directory service domain of the user attempting
        access to the RHEVM. This takes the form of [username]@[domain].
        :param admin_pwd: The password for the user attempting access to the RHEVM.
        :return:
        """
        api_url = f"{self.rhevm_url()}/api"
        ca_file = "/etc/pki/ovirt-engine/ca.pem"
        options = "insecure = False\n" \
                  "no_paging = False\n" \
                  "filter = False\n" \
                  "timeout = -1"
        rhevm_shellrc = '/root/.ovirtshellrc'
        cmd = f"echo -e '[ovirt-shell]\n" \
            f"username = {admin_user}\n" \
            f"password = {admin_pwd}\n" \
            f"ca_file = {ca_file}\n" \
            f"url = {api_url}\n" \
            f"{options}' > {rhevm_shellrc}"
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
            hosts = output.strip().split('\n')
        else:
            hosts = list()
        logger.info(f"Get RHEVM Host: {hosts}")
        return hosts

    def guest_search(self, guest_name):
        """
        Search the specific guest, return the expected attributes
        :param guest_name: name for the specific guest
        :param uuid_info: if you need the uuid_info: guest_uuid, esx_uuid, esx_hwuuid
        :return: guest attributes, exclude guest_name, guest_ip, guest_uuid ...
                 guest_state: guest_poweron:1, guest_poweroff:0, guest_Suspended:2
                 esx_state: host_poweron:1, host_poweroff:0
        """
        host_id = self.get_rhevm_info("vm", guest_name, 'host-id')
        cluster_id = self.get_rhevm_info("vm", guest_name, 'cluster-id')
        guest_msgs = {
            'guest_name': guest_name,
            'guest_ip': '',
            'guest_uuid': self.get_rhevm_info("vm", guest_name, 'id'),
            'guest_state': self.get_rhevm_info("vm", guest_name, 'status-state'),
            'vdsm_uuid': host_id,
            'vdsm_hwuuid': self.get_rhevm_info("host", host_id, 'hardware_information-uuid'),
            'vdsm_hostname': self.get_rhevm_info("host", host_id, 'name'),
            'vdsm_version': self.get_rhevm_info("host", host_id, 'version-full_version'),
            'vdsm_cpu': self.get_rhevm_info("host", host_id, 'cpu-topology-sockets'),
            'vdsm_cluster': self.get_rhevm_info("cluster", cluster_id, 'name'),
        }
        return guest_msgs

    def get_rhevm_info(self, object_type, object_id, value):
        """
        Get the info frmo rhevm
        :param object_type: The type of object to retrieve, such as vm, host, cluster and so on.
        :param object_id:  <id|name> The object identifier or the object identifier
        :param value: the value you want to get from the result
        :return: the value you want to get
        """
        cmd = f"ovirt-shell -c -E 'show {object_type} {object_id}' |grep '^{value}'"
        ret, output = self.ssh.runcmd(cmd)
        if not ret and value in output:
            result = output.strip().split(':')[1].strip()
            logger.info(f"Succeeded to get rhevm {object_type} ({object_id}) {value}: {result}")
            return result
        else:
            logger.info(f"Failed to get rhevm {object_type} ({object_id}) {value}")
