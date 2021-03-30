import json
import re

from hypervisor import FailException
from hypervisor import logger
from hypervisor.ssh import SSHConnect


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
        if ret is 0 and stdout is not None:
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

    def guest_add(self, host, host_ssh_user, host_ssh_pwd, guest_name, image_path):
        """
        Create a new virtual machine.
        :param host: the host on which you want to create the new virtual machine.
        :param host_ssh_user: the ssh username for the host
        :param host_ssh_pwd: the ssh password for the host
        :param guest_name: the name for the new virtual machine
        :param image_path: the path for the guest image
        :return:
        """
        self.guest_images(host, host_ssh_user, host_ssh_pwd, guest_name, image_path)
        data_store = self.host_search(host)["host_data_store"]
        vmxFile = f"'[{data_store}] {guest_name}/{guest_name}.vmx'"
        cmd = f'{self.cert} New-VM -VMFilePath {vmxFile} -VMHost {host}'
        ret, _ = self.ssh.runcmd(cmd)
        if not ret and self.guest_exist(guest_name):
            logger.info("Succeeded to add vcenter guest")
        else:
            raise FailException("Failed to add vcenter guest")
        return self.guest_start(guest_name)

    def guest_del(self, guest_name):
        """
        Remove the specified virtual machines from the vCenter Server system.
        :param guest_name: the virtual machines you want to remove.
        :return:
        """
        if self.guest_search(guest_name)['guest_state'] is not 1:
            self.guest_stop(guest_name)
        cmd = f'{self.cert} Remove-VM -VM {guest_name} -DeletePermanently -Confirm:$false'
        ret, _ = self.ssh.runcmd(cmd)
        if not ret and not self.guest_exist(guest_name):
            logger.info("Succeeded to delete vcenter guest")
        else:
            raise FailException("Failed to delete vcenter guest")

    def guest_exist(self, guest_name):
        """
        Check if the esx guest exists
        :param guest_name: the name for the guest
        :return:
        """
        cmd = f'{self.cert} Get-VM -Name {guest_name}'
        ret, _ = self.ssh.runcmd(cmd)
        if ret:
            return False
        else:
            return True

    def guest_images(self, host, host_ssh_user, host_ssh_pwd, guest_name, image_path):
        """
        Prepare the guest image
        :param host: the host on which you want to create the new virtual machine.
        :param host_ssh_user: the ssh username for the host
        :param host_ssh_pwd: the ssh password for the host
        :param guest_name: the name for the new virtual machine
        :param image_path: the path for the guest image
        :return:
        """
        host_ssh = SSHConnect(host, user=host_ssh_user, pwd=host_ssh_pwd)
        cmd = f'rm -rf /vmfs/volumes/datastore*/{guest_name}*; ' \
            f'wget -P /vmfs/volumes/datastore* {image_path}'
        ret, output = host_ssh.runcmd(cmd)
        if ret:
            raise FailException("Failed to download guest image")
        cmd = f'tar -zxvf /vmfs/volumes/datastore*/{guest_name}.tar.gz ' \
            f'-C /vmfs/volumes/datastore*/'
        ret, output = host_ssh.runcmd(cmd)
        if ret:
            raise FailException("Failed to uncompress guest image")
        cmd = "rm -f /vmfs/volumes/datastore*/*.tar.gz"
        host_ssh.runcmd(cmd)

    def guest_resume(self, guest_name):
        """
        Resume virtual machines
        :param guest_name: the virtual machines you want to resume.
        :return:
        """
        cmd = f'{self.cert} Start-VM -VM {guest_name} -Confirm:$false'
        ret, _ = self.ssh.runcmd(cmd)
        if not ret and self.guest_search(guest_name)['guest_state'] is 1:
            logger.info("Succeeded to resume vcenter guest")

    def guest_search(self, guest_name, uuid_info=False):
        """
        Search the specific guest, return the expected attributes
        :param guest_name: name for the specific guest
        :param uuid_info: if you need the uuid_info: guest_uuid, esx_uuid, esx_hwuuid
        :return: guest attributes, exclude guest_name, guest_ip, guest_uuid ...
                 guest_state: guest_poweron:1, guest_poweroff:0, guest_Suspended:2
                 esx_state: host_poweron:1, host_poweroff:0
        """
        cmd = f'{self.cert} ConvertTo-Json @(' \
            f'Get-VM {guest_name} | Select * -ExcludeProperty ExtensionData)'
        ret, output = self.ssh.runcmd(cmd)
        output = self._format(ret, output)[0]
        host_name = output["VMHost"]["Name"]
        guest_ip = output["Guest"]["IPAddress"].split()[0] \
            if output["Guest"]["IPAddress"] else None
        guest_msgs = {
            'guest_name': output['Name'],
            'guest_ip': guest_ip,
            'guest_state': output["PowerState"],
            'guest_cpu': output["NumCpu"],
            'esx_ip': output["VMHost"]["Name"],
            'esx_hostname': output["VMHost"]["Name"],
            'esx_version': output["VMHost"]["Version"],
            'esx_state': output["VMHost"]["PowerState"],
            'esx_cpu': output["VMHost"]["NumCpu"],
            'esx_cluster': output["VMHost"]["Parent"]
        }
        if uuid_info:
            guest_msgs['guest_uuid'] = self.guest_uuid(guest_name)
            guest_msgs['esx_uuid'] = self.host_uuid(host_name)
            guest_msgs['esx_hwuuid'] = self.host_hwuuid(host_name)
        return guest_msgs

    def guest_start(self, guest_name):
        """
        Power on virtual machines.
        :param guest_name: the virtual machines you want to power on.
        :return:
        """
        cmd = f'{self.cert} Start-VM -VM {guest_name} -Confirm:$false'
        ret, _ = self.ssh.runcmd(cmd)
        if not ret and self.guest_search(guest_name)['guest_state'] is 1:
            logger.info("Succeeded to start vcenter guest")
            return self.guest_search(guest_name)['guest_ip']

    def guest_stop(self, guest_name):
        """
        Power off virtual machines.
        :param guest_name: the virtual machines you want to power off.
        :return:
        """
        cmd = f'{self.cert} Stop-VM -VM {guest_name} -Kill -Confirm:$false'
        ret, _ = self.ssh.runcmd(cmd)
        if not ret and self.guest_search(guest_name)['guest_state'] is 0:
            logger.info("Succeeded to stop vcenter guest")

    def guest_suspend(self, guest_name):
        """
        Suspend virtual machines.
        :param guest_name: the virtual machines you want to suspend.
        :return:
        """
        cmd = f'{self.cert} Suspend-VM -VM {guest_name} -Confirm:$false'
        ret, _ = self.ssh.runcmd(cmd)
        if not ret and self.guest_search(guest_name)['guest_state'] is 2:
            logger.info("Succeeded to suspend vcenter guest")

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

    def host_add(self, location, host_name, host_user, host_pwd):
        """
        Add a host to be managed by a vCenter Server system.
        :param location: the datacenter or folder where you want to place the host.
        :param host_name: the name of the host you want to add to a vCenter Server system.
        :param host_user: the user name you want to use for authenticating with the host.
        :param host_pwd: the password you want to use for authenticating with the host.
        :return:
        """
        if self.host_exist(host_name):
            logger.warning('This host is already being managed by this vSphere')
            return
        cmd = f'{self.cert} Add-VMHost {host_name} ' \
            f'-Location {location} ' \
            f'-User {host_user} ' \
            f'-Password {host_pwd} ' \
            f'-confirm:$false'
        self.ssh.runcmd(cmd)
        if not self.host_exist(host_name):
            raise FailException(f'Failed to add VMHost {host_name}')

    def host_del(self, host_name):
        """
        Remove the specified hosts from the inventory.
        Note: need to set it's state to Disconnected firstly.
        :param host_name: the host you want to remove.
        :return:
        """
        self.host_set(host_name, "Disconnected")
        cmd = f'{self.cert} Remove-VMHost {host_name} -confirm:$false'
        self.ssh.runcmd(cmd)
        if self.host_exist(host_name):
            raise FailException(f'Failed to delete esx host {host_name}')

    def host_exist(self, host_name):
        """
        Check if the esx host exists
        :param host_name: mater name
        :return: host exist, return True, else, return False
        """
        cmd = f'{self.cert} Get-VMHost -Name {host_name}'
        ret, output = self.ssh.runcmd(cmd)
        if ret is 0:
            return True
        else:
            return False

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

    def host_restart(self, host_name):
        """
        Restart the specified hosts.
        :param host_name: the hosts you want to restart.
        :return:
        """
        cmd = f'{self.cert} Restart-VMHost {host_name} -force -confirm:$false'
        ret, _ = self.ssh.runcmd(cmd)
        if ret:
            raise FailException(f'Failed to find restart host {host_name}')

    def host_search(self, host_name):
        """
        Search the specific guest, return the expected attributes
        :param host_name: the host name for esx
        :return: host messages
        """
        cmd = f'{self.cert} ConvertTo-Json @(' \
            f'Get-VMHost {host_name} | Select * -ExcludeProperty ExtensionData)'
        ret, output = self.ssh.runcmd(cmd)
        output = self._format(ret, output)[0]
        host_msgs = {
            'host_ip': output["Name"],
            'host_state': output["State"],
            'host_connection_state': output["ConnectionState"],
            'host_power_state': output["PowerState"],
            'host_cpu': output["NumCpu"],
            'host_cluster': output["Parent"]["Name"]
        }
        if host_msgs['host_power_state']:
            host_msgs['host_data_store'] = output["StorageInfo"]["FileSystemVolumeInfo"].strip()
        return host_msgs

    def host_set(self, host_name, state):
        """
        Modify the configuration of the host.
        :param host_name: the host you want to configure.
        :param state: Connected or Disconnected or Maintenance.
        :return:
        """
        cmd = f'{self.cert} Set-VMHost {host_name} -State {state}'
        ret, _ = self.ssh.runcmd(cmd)
        if ret:
            raise FailException(f'Failed to set host {host_name} to {state} state')

    def host_start(self, host_name):
        """
        Start the specified hosts.
        :param host_name: the hosts you want to start.
        :return:
        """
        cmd = f'{self.cert} Start-VMHost {host_name} -confirm:$false'
        ret, _ = self.ssh.runcmd(cmd)
        if ret:
            raise FailException(f'Failed to start esx host {host_name}')

    def host_stop(self, host_name):
        """
        Power off the specified hosts.
        :param host_name: The host you want to power off.
        :return:
        """
        if not self.host_exist(host_name):
            raise FailException(f'Failed to find esx host {host_name}')
        cmd = f'{self.cert} Stop-VMHost {host_name} -force -confirm:$false'
        ret, _ = self.ssh.runcmd(cmd)
        if ret:
            raise FailException(f'Failed to stop host {host_name}')

    def host_uuid(self, host_name):
        """
        Get uuid for esx host
        :param host_name: the host name for esx
        :return: uuid for esx host
        """
        sysinfo = "%{(Get-View $_.Id).Hardware.SystemInfo}"
        cmd = f'{self.cert} ConvertTo-Json @(Get-VMHost -Name {host_name} | {sysinfo})'
        ret, output = self.ssh.runcmd(cmd)
        output = self._format(ret, output)[0]
        return output["Uuid"]
