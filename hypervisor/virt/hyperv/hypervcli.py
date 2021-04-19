import json
import re

from hypervisor import logger
from hypervisor.ssh import SSHConnect


class HypervCLI:
    def __init__(self, server, ssh_user, ssh_passwd):
        """
        Collect hyperv information, provide Guest add/delete/start/stop/suspend/resume functions
        via PowerCli Command line
        :param server: the ip for the hyperv server
        :param ssh_user: the ssh user for the hyperv server
        :param ssh_passwd: the ssh password for the hyperv server
        """
        self.server = server
        self.ssh_user = ssh_user
        self.ssh_passwd = ssh_passwd
        self.ssh = SSHConnect(self.server, user=self.ssh_user, pwd=self.ssh_passwd)

    def _format(self, ret=0, stdout=None):
        """
        Convert the json string to python list data
        :param ret: return code
        :param stdout: output for the execute command
        :return: the list after json.loads
        """
        stdout = re.findall(r'[[][\W\w]+[]]', stdout)[0]
        if ret is 0 and stdout is not None:
            return json.loads(stdout)

    def info(self):
        """
        Get the VMhost info
        :return: the VMHosts info
        """
        cmd = 'PowerShell ConvertTo-Json @(Get-VMHost)'
        ret, output = self.ssh.runcmd(cmd)
        output = self._format(ret, output)
        for host in output:
            logger.info(f"Get Hyperv master: {host['Name']}")
        return output

    def guest_search(self, guest_name, uuid_info=False):
        """
        Search the specific guest, return the expected attributes
        :param guest_name: name for the specific guest
        :param uuid_info: if you need the uuid_info: guest_uuid, hyperv_uuid, hyperv_hwuuid
        :return: guest attributes, exclude guest_name, guest_ip, guest_uuid ...
                 guest_state: guest_poweron:1, guest_poweroff:0, guest_Suspended:2
                 hyperv_state: host_poweron:1, host_poweroff:0
        """
        cmd = f'PowerShell ConvertTo-Json @(Get-VM {guest_name})'
        ret, output = self.ssh.runcmd(cmd)
        output = self._format(ret, output)[0]
        guest_msgs = {
            'guest_name': output['VMName'],
            'guest_ip': self.guest_ip(guest_name),
            'guest_state': output['State'],
            'hyperv_ip': self.server,
            'hyperv_hostname': output['ComputerName'],
            'hyperv_version': output['Version'],
            'hyperv_cpu': output['CPUUsage'],
        }
        if uuid_info:
            guest_msgs['guest_uuid'] = self.guest_uuid()
            guest_msgs['hyperv_uuid'] = self.host_uuid()
        return guest_msgs

    def guest_ip(self, guest_name):
        """
        Get ip for hyperv guest
        :param guest_name: the guest name for hyperv guest
        :return: the ip for hyperv guest
        """
        cmd = f'PowerShell (Get-VMNetworkAdapter -VMName {guest_name}).IpAddresses'
        ret, output = self.ssh.runcmd(cmd)
        return output.split()[0]

    def guest_uuid(self):
        """
        Get uuid for hyperv guest
        :param guest_name: the guest name for hyperv guest
        :return: uuid for hyperv guest
        """
        cmd = 'PowerShell (gwmi -Namespace Root\Virtualization\V2 ' \
              '-ClassName Msvm_VirtualSystemSettingData).BiosGUID'
        ret, output = self.ssh.runcmd(cmd)
        return output

    def host_uuid(self):
        """
        Get uuid for hyper host
        :param host_name: the host name for hyperv
        :return: uuid for hyperv host
        """
        cmd = "PowerShell ConvertTo-Json @(" \
              "gwmi -namespace 'root/cimv2' Win32_ComputerSystemProduct | select *)"
        ret, output = self.ssh.runcmd(cmd)
        output = self._format(ret, output)[0]
        return output["UUID"]


