import re
import json
from hypervisor.log import getLogger
from hypervisor.ssh import SSHConnect

logger = getLogger(__name__)


class PowerCLI:
    def __init__(self, server, admin_user, admin_passwd, ssh_user, ssh_passwd):
        """
        Collect vcenter information, provide Host add/delete and
        Guest add/delete/start/stop/suspend/resume functions
        via Powercli Command line
        :param server: the ip for the vcenter server
        :param admin_user: the user for the vcenter server
        :param admin_passwd: the password for the vcenter server
        :param ssh_user: the ssh user for the vcenter server
        :param ssh_passwd: the ssh password for the center server
        """
        self.server = server
        self.admin_user = admin_user
        self.admin_passwd = admin_passwd
        self.ssh_user = ssh_user
        self.ssh_passwd = ssh_passwd
        self.cert = (
            f'powershell Connect-VIServer '
            f'-Server {self.server} '
            f'-Protocol https '
            f'-User {self.admin_user} '
            f'-Password {self.admin_passwd};'
        )
        self.ssh = SSHConnect(self.server, user=self.ssh_user, pwd=self.ssh_passwd)

    def _format(self, ret=0, stdout=None):
        """
        Convert the json string to python list data
        :param ret: return code
        :param stdout: output for the execute command
        :return: the list after json.loads
        """
        stdout = re.findall(r'[[][\W\w]+[]]', stdout)[0]
        if ret == 0 and stdout is not None:
            return json.loads(stdout)

    def info(self):
        """
        Get the VMhost info
        :return: the VMHosts info
        """
        cmd = f'{self.cert} ConvertTo-Json @(Get-VMHost | Select * -ExcludeProperty ExtensionData)'
        ret, output = self.ssh.runcmd(cmd)
        output = self._format(ret, output)
        for host in output:
            logger.info(f"Get ESXi Host: {host['Name']}")
        return output

    def guest_search(self, guest_name):
        """
        Search the specific guest, return the expected attributes
        :param guest_name: name for the specific guest
        :return: guest attributes, exclude guest_name, guest_ip, guest_uuid ...
        """
        cmd = f'{self.cert} ConvertTo-Json @(' \
            f'Get-VM {guest_name} | Select * -ExcludeProperty ExtensionData)'
        ret, output = self.ssh.runcmd(cmd)
        output = self._format(ret, output)[0]
        host_name = output["VMHost"]["Name"]
        guest_msgs = {
            'guest_name': output['Name'],
            'guest_ip': output["Guest"]["IPAddress"].split()[0],
            'guest_uuid': self.guest_uuid(guest_name),
            'guest_state': output["Guest"]["State"],
            'guest_cpu': output["NumCpu"],
            'esx_ip': output["VMHost"]["Name"],
            'esx_uuid': self.host_uuid(host_name),
            'esx_hwuuid': self.host_hwuuid(host_name),
            'esx_hostname': output["VMHost"]["Name"],
            'esx_version': output["VMHost"]["Version"],
            'esx_state': output["VMHost"]["State"],
            'esx_cpu': output["VMHost"]["NumCpu"],
            'esx_cluster': output["VMHost"]["Parent"]
        }
        return guest_msgs

    def guest_uuid(self, guest_name):
        """
        Get uuid for esx guest
        :param guest_name: the guest name for esx guest
        :return: uuid for esx guest
        """
        config = "%{(Get-View $_.Id).config}"
        cmd = f'{self.cert} ConvertTo-Json @(Get-VM {guest_name} | {config})'
        ret, output = self.ssh.runcmd(cmd)
        output = self._format(ret, output)[0]
        return output["Uuid"]

    def host_uuid(self, host_name):
        """
        Get uuid for esx host
        :param host_name: the host uuid for esx
        :return: uuid for esx host
        """
        sysinfo = "%{(Get-View $_.Id).Hardware.SystemInfo}"
        cmd = f'{self.cert} ConvertTo-Json @(Get-VMHost -Name {host_name} | {sysinfo})'
        ret, output = self.ssh.runcmd(cmd)
        output = self._format(ret, output)[0]
        return output["Uuid"]

    def host_hwuuid(self, host_name):
        """
        Get hwuui for esx host
        :param host_name: the host name for esx
        :return: hwuuid for esx host
        """
        moref = "%{(Get-View $_.Id).MoRef}"
        cmd = f'{self.cert} ConvertTo-Json @(Get-VMHost -Name {host_name} | {moref})'
        ret, output = self.ssh.runcmd(cmd)
        output = self._format(ret, output)[0]
        return output["Value"]

    def host_add(self):
        pass

    def host_del(self):
        pass

    def guest_add(self):
        pass

    def guest_del(self):
        pass

    def guest_start(self):
        pass

    def guest_stop(self):
        pass

    def guest_suspend(self):
        pass

    def guest_resume(self):
        pass
