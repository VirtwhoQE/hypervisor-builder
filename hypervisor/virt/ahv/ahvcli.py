import json

from hypervisor import FailException
from hypervisor import logger
from hypervisor.ssh import SSHConnect


class AHVaCLI:
    def __init__(self, server, ssh_user, ssh_pwd):
        """
        Collect AHV information, provide Guest add/delete/start/stop/suspend/resume functions
        via aCLI command line following 'https://portal.nutanix.com/page/documents/details?
        targetId=Command-Ref-AOS-v6_0:man-acli-c.html' and nCLI command line following
        'https://portal.nutanix.com/page/documents/details
        ?targetId=Command-Ref-AOS-v6_0:man-ncli-c.html'
        :param server: the ip for the AHV server
        :param ssh_user: the ssh user for the AHV server
        :param ssh_pwd: the ssh password for the AHV server
        """
        self.acli = "/usr/local/nutanix/bin/acli"
        self.ncli = "/home/nutanix/prism/cli/ncli"
        self.server = server
        self.ssh_user = ssh_user
        self.ssh_pwd = ssh_pwd
        self.ssh = SSHConnect(self.server, user=self.ssh_user, pwd=self.ssh_pwd)
        self.set_json_ouput()

    def _format(self, stdout):
        """
        Convert the json string to python dict data for aCLI command
        :param stdout: output for the execute command
        :return: the data after json.loads
        """
        output = json.loads(stdout)
        if output["status"] is 0:
            return output["data"]

    def set_json_ouput(self):
        """
        Set the output to JSON format for aCLI command
        :return:
        """
        ret, output = self.ssh.runcmd(f"{self.acli} get json")
        if "json=False" in output:
            self.ssh.runcmd(f'sed -i "s|^json.*|json=1|g" {self.acli}')
            ret, output = self.ssh.runcmd(f"{self.acli} get json")
        if '"value": true' in output:
            logger.info("Succeeded to set JSON format output")
        else:
            FailException("Failed to set JSON format output")

    def get_ncli_info(self, cmd, value):
        """
        Get the info from AHV by nCLI command.
        :param cmd:
        :param value: the name of value you want to get from the result
        :return: the value you want to get
        """
        ret, output = self.ssh.runcmd(f"{self.ncli} {cmd}")
        ncli_info = {}
        for line in output.split("\n"):
            if not ret and value in line:
                result = line.split(":", 1)
                ncli_info[result[0].strip()] = result[1].strip()
                logger.info(f"Succeeded to get {value}: {ncli_info[value]}")
                return ncli_info[value]
        else:
            logger.info(f"Failed to get {value}")
            return None

    def get_acli_info(self, namespace, value):
        """
        Gets the current value of the given configuration options
        For example:
            get_acli_info('vm', 'rhel84_guest') means aCLI command:
            alic vm.get rhel84_guest
        :param namespace: the namespace of the options
        :param value: identifier, like id, or name
        :return: the dict info of the virtual machines
        """
        cmd = f"{self.acli} {namespace}.get {value}"
        ret, output = self.ssh.runcmd(cmd)
        output = self._format(output)
        for msg in output.values():
            return msg

    def get_guest_info_ncli(self, guest_name):
        """
        Get the guest details for virtual machine by nCLI
        :param guest_name: Name of the Virtual Machine
        :return: the guest details
        """
        cmd = f"{self.ncli} virtualmachine list name='{guest_name}'"
        ret, output = self.ssh.runcmd(cmd)
        guest_info = {}
        for line in output.strip().split("\n"):
            result = line.split(":", 1)
            guest_info[result[0].strip()] = result[1].strip()
        return guest_info

    def guest_search(self, guest_name):
        """
        Search the specific guest, return the expected attributes
        :param guest_name: name for the specific guest
        :return: guest attributes, include guest_name, guest_ip, guest_uuid, guest_state,
        uuid, hostname, version, cpu and cluster.
            for guest_state:
                'kOn' : Power on
                'kOff': Power off
        """
        guest_info_acli = self.get_acli_info("vm", guest_name)
        guest_info_ncli = self.get_guest_info_ncli(guest_name)
        guest_msgs = {
            "guest_name": guest_info_acli["config"]["name"],
            "guest_ip": guest_info_ncli["VM IP Addresses"],
            "guest_uuid": guest_info_ncli["Uuid"],
            "guest_state": guest_info_acli["state"],
            "uuid": guest_info_acli["host_uuid"],
            "hostname": guest_info_ncli["Hypervisor Host Name"],
            "version": self.get_ncli_info(
                f"host list id={guest_info_ncli['Hypervisor Host Id']}",
                "Hypervisor Version",
            ),
            "cpu": self.get_acli_info("host", guest_info_ncli["Hypervisor Host Uuid"])[
                "num_cpus"
            ],
            "cluster": self.get_ncli_info("cluster info", "Cluster Name"),
        }
        return guest_msgs
