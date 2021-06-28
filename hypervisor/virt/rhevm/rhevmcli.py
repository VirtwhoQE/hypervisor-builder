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
        api_url = "{0}/api".format(admin_server)
        ca_file = "/etc/pki/ovirt-engine/ca.pem"
        options = "insecure = False\nno_paging = False\nfilter = False\ntimeout = -1"
        cmd = "echo -e '[ovirt-shell]\nusername = {0}\npassword = {1}\nca_file = {2}\nurl = {3}\n{4}' > {5}"\
                .format(admin_user, admin_passwd, ca_file, api_url, options, "/root/.ovirtshellrc")
        self.ssh.runcmd(cmd)
        self.ssh.runcmd("ovirt-aaa-jdbc-tool user unlock admin")
        cmd = "{0} -c -E  'ping'".format("ovirt-shell")
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and "success" in output:
            logger.info("Succeeded to config rhevm({0}) shell".format(self.server))
        else:
            raise FailException("Failed to config rhevm({0}) shell".format(self.server))

    def info(self):
        """
        Get the VMhost info
        :return: the VMHosts info
        """
        cmd = "ovirt-shell -c -E 'list hosts' | grep '^name' | awk -F ':' '{print $2}'"
        ret, output = self.ssh.runcmd(cmd)
        if ret == 0 and output is not None and output != "":
            hosts = output.strip().split('\n')
        else:
            hosts = list()
        logger.info(f"Get RHEVM Host: {hosts}")
        return hosts
