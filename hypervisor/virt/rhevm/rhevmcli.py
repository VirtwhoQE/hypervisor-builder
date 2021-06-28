import json
import re

from hypervisor import FailException
from hypervisor import logger
from hypervisor.ssh import SSHConnect

class RHVMCLI:
    def __init__(self, server, ssh_user, ssh_pwd):
        """
        Collect rhevm information, provide Guest add/delete/start/stop/suspend/resume functions
        via ovirt-shell Command line
        :param server: the ip for the rhevm server
        :param ssh_user: the ssh user for the rhevm server
        :param ssh_pwd: the ssh password for the rhevm server
        """
        self.server = server
        self.ssh_user = ssh_user
        self.ssh_pwd = ssh_pwd
        self.ssh = SSHConnect(self.server, user=self.ssh_user, pwd=self.ssh_pwd)

    def rhevm_shell_config(self, admin_server, admin_user, admin_passwd):
        """
        config the rhevm shell, connect to the rhevm server
        :param admin_server: ip for the server
        :param admin_user: username for the account
        :param admin_passwd: password for the account
        :return:
        """
        api_url = f"{admin_server}/api"
        ca_file = "/etc/pki/ovirt-engine/ca.pem"
        options = "insecure = False\n" \
                  "no_paging = False\n" \
                  "filter = False\n" \
                  "timeout = -1"
        rhevm_shellrc = '/root/.ovirtshellrc'
        cmd = f"echo -e '[ovirt-shell]\n" \
            f"username = {admin_user}\n" \
            f"password = {admin_passwd}\n" \
            f"ca_file = {ca_file}\n" \
            f"url = {api_url}\n" \
            f"{options}' > {rhevm_shellrc}"
        self.ssh.runcmd(cmd)
        self.ssh.runcmd("ovirt-aaa-jdbc-tool user unlock admin")
        cmd = f"ovirt-shell -c -E  'ping'"
        ret, output = self.ssh.runcmd(cmd)
        if not ret and "success" in output:
            logger.info(f"Succeeded to config rhevm({self.server}) shell")
        else:
            raise FailException(f"Failed to config rhevm({self.server}) shell")

    def info(self):
        """
        Get the VMhost info
        :return: the VMHosts info
        """
        cmd = "ovirt-shell -c -E 'list hosts' | grep '^name' | awk -F ':' '{print $2}'"
        ret, output = self.ssh.runcmd(cmd)
        if not ret and output is not None and output != "":
            hosts = output.strip().split('\n')
        else:
            hosts = list()
        logger.info(f"Get RHEVM Host: {hosts}")
        return hosts
