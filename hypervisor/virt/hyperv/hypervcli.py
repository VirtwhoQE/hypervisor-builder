import json
import re

from hypervisor import logger
from hypervisor.ssh import SSHConnect


class HypervCLI:
    def __init__(self, server, ssh_user, ssh_pwd):
        """
        Collect hyperv information, provide Guest add/delete/start/stop/suspend/resume functions
        via PowerCli Command line
        :param server: the ip for the hyperv server
        :param ssh_user: the ssh user for the hyperv server
        :param ssh_pwd: the ssh password for the hyperv server
        """
        self.server = server
        self.ssh_user = ssh_user
        self.ssh_pwd = ssh_pwd
        self.ssh = SSHConnect(self.server, user=self.ssh_user, pwd=self.ssh_pwd)

    def _format(self, ret=0, stdout=None):
        """
        Convert the json string to python list data
        :param ret: return code
        :param stdout: output for the execute command
        :return: the list after json.loads
        """
        stdout = re.findall(r"[[][\W\w]+[]]", stdout)[0]
        if ret == 0 and stdout is not None:
            return json.loads(stdout)

    def guest_search(self, guest_name):
        """
        Search the specific guest, return the expected attributes
        :param guest_name: name for the specific guest
        :return: guest attributes, exclude guest_name, guest_ip, guest_uuid ...
                 guest_state: guest_poweron:2, guest_poweroff:3, guest_Suspended:9
        """
        guest_info = self.guest_info(guest_name, guest_uuid=True, guest_ip=True)
        host_info = self.host_info()
        guest_data = dict(guest_info, **host_info)
        return guest_data

    def host_info(self):
        """
        Get ip, hostname, version cpu and uuid for hyperv host
        :return: a dict
        """
        cmd = """PowerShell ConvertTo-Json @("gwmi -namespace 'root/cimv2' Win32_ComputerSystemProduct | select *")"""
        ret, output = self.ssh.runcmd(cmd)
        output = self._format(ret, output)[0]
        host_info = {
            "hyperv_ip": self.server,
            "hyperv_hostname": output["PSComputerName"],
            # 'hyperv_version': '',
            "hyperv_cpu": str(output["__GENUS"]),
            "hyperv_uuid": output["UUID"],
        }
        return host_info

    def guest_info(self, guest_name, guest_uuid=False, guest_ip=False):
        """
        Search the specific guest, return the guest info
        :param guest_name: name for the specific guest
        :return: guest attributes, exclude guest_name, guest_ip, guest_uuid ...
                 guest_state: guest_poweron:2, guest_poweroff:3, guest_Suspended:9
        """
        cmd = f"PowerShell ConvertTo-Json @(Get-VM {guest_name})"
        ret, output = self.ssh.runcmd(cmd)
        output = self._format(ret, output)[0]
        guest_info = {"guest_name": output["VMName"], "guest_state": output["State"]}
        if guest_uuid:
            guest_info["guest_uuid"] = self.guest_uuid()
        if guest_ip:
            guest_info["guest_ip"] = self.guest_ip(guest_name)
        return guest_info

    def guest_ip(self, guest_name):
        """
        Get ip for hyperv guest
        :param guest_name: the guest name for hyperv guest
        :return: the ip for hyperv guest
        """
        cmd = f"PowerShell (Get-VMNetworkAdapter -VMName {guest_name}).IpAddresses"
        ret, output = self.ssh.runcmd(cmd)
        return output.split()[0] if output else None

    def guest_uuid(self):
        """
        Get uuid for hyperv guest
        :return: uuid for hyperv guest
        """
        cmd = (
            "PowerShell (gwmi -Namespace Root\Virtualization\V2 "
            "-ClassName Msvm_VirtualSystemSettingData).BiosGUID"
        )
        ret, output = self.ssh.runcmd(cmd)
        return output.strip()

    def virtual_switch(self):
        """
        Get the name for the virtual network switch
        :return: the virtual switch name
        """
        cmd = "PowerShell ConvertTo-Json @(Get-VMSwitch)"
        ret, output = self.ssh.runcmd(cmd)
        output = self._format(ret, output)[0]
        return output["Name"]

    def guest_image(self, guest_name, image_path):
        """
        Prepare the guest image for hyperv hypervisor
        :param guest_name: the name for the new virtual machine
        :param image_path: the path for the guest image
        :return:
        """
        cmd = "PowerShell New-Item -path C:\ -Name hyperv_img -Type Directory"
        self.ssh.runcmd(cmd)
        cmd = "PowerShell Get-ChildItem C:\hyperv_img"
        ret, output = self.ssh.runcmd(cmd)
        if not ret and guest_name in output:
            logger.info("hyperv image is exist")
            return True
        else:
            cmd = (
                f"PowerShell (New-Object System.Net.WebClient).DownloadFile("
                f"'{image_path}', 'C:\hyperv_img\{guest_name}.vhdx')"
            )
            ret, output = self.ssh.runcmd(cmd)
            if not ret:
                logger.info("succeeded to download hyperv image")
                return True
            logger.error("Failed to download hyperv image")
            return False

    def guest_exist(self, guest_name):
        """
        Check if the hyperv guest exists
        :param guest_name: the name for the guest
        :return: guest exists, return True, else, return False.
        """
        cmd = "PowerShell Get-VM"
        ret, output = self.ssh.runcmd(cmd)
        if not ret and guest_name in output:
            logger.info(f"Succeed to find guest {guest_name }")
            return True
        else:
            logger.info(f"Failed to find guest {guest_name}")
            return False

    def guest_add(self, guest_name, image_path):
        """
        Create a new virtual machine.
        :param guest_name: the name for the new virtual machine
        :param image_path: the path for the guest image which from the remote web
        :return: guest already existed, return None,
                 create successfully, return True,
                 else, return False
        """
        if self.guest_exist(guest_name):
            logger.warning(f"Guest {guest_name} has already existed")
            return True
        if self.guest_image(guest_name, image_path):
            switch_name = self.virtual_switch()
            if "8." in guest_name:
                options = (
                    f"-MemoryStartupBytes 2GB -SwitchName {switch_name} -Generation 2"
                )
            else:
                options = (
                    f"-MemoryStartupBytes 1GB -SwitchName {switch_name} -Generation 1"
                )
            cmd = f'PowerShell New-VM -Name {guest_name} -VHDPath "C:\hyperv_img\{guest_name}.vhdx" {options}'
            ret, _ = self.ssh.runcmd(cmd)
            if not ret and self.guest_exist(guest_name):
                logger.info("Succeeded to add hyperv guest")
                if "8." in guest_name:
                    cmd = f"PowerShell Set-VMFirmware -VMName {guest_name} -EnableSecureBoot off"
                    self.ssh.runcmd(cmd)
                return True
            else:
                logger.error("Failed to add hyperv guest")
                return False
        else:
            return False

    def guest_del(self, guest_name):
        """
        Remove the specified virtual machines from the hyperv Server system.
        :param guest_name: the virtual machines you want to remove.
        :return: remove successfully, return True, else, return False.
        """
        if self.guest_info(guest_name)["guest_state"] != 3:
            self.guest_stop(guest_name)
        cmd = f"PowerShell Remove-VM {guest_name} -force"
        ret, _ = self.ssh.runcmd(cmd)
        if not ret and not self.guest_exist(guest_name):
            logger.info("Succeeded to delete hyperv guest")
            return True
        else:
            logger.error("Failed to delete hyperv guest")
            return False

    def guest_start(self, guest_name):
        """
        Power on virtual machines.
        :param guest_name: the virtual machines you want to power on.
        :return: power on successfully, return True, else, return False.
        """
        cmd = f"PowerShell Start-VM -Name {guest_name}"
        ret, _ = self.ssh.runcmd(cmd)
        if not ret and self.guest_info(guest_name)["guest_state"] == 2:
            logger.info("Succeeded to start hyperv guest")
            return True
        else:
            logger.error("Failed to start hyperv guest")
            return False

    def guest_stop(self, guest_name):
        """
        Power off virtual machines.
        :param guest_name: the virtual machines you want to power off.
        :return: stop successfully, return True, else, return False.
        """
        cmd = f"PowerShell Stop-VM -Name {guest_name}"
        ret, _ = self.ssh.runcmd(cmd)
        if not ret and self.guest_info(guest_name)["guest_state"] == 3:
            logger.info("Succeeded to stop hyperv guest")
            return True
        else:
            logger.error("Failed to stop hyperv guest")
            return False

    def guest_suspend(self, guest_name):
        """
        Suspend virtual machines.
        :param guest_name: the virtual machines you want to suspend.
        :return: suspend successfully, return True, else, return False.
        """
        cmd = f"PowerShell Suspend-VM -Name {guest_name}"
        ret, _ = self.ssh.runcmd(cmd)
        if not ret and self.guest_info(guest_name)["guest_state"] == 9:
            logger.info("Succeeded to suspend hyperv guest")
            return True
        else:
            logger.error("Failed to suspend hyperv guest")
            return False

    def guest_resume(self, guest_name):
        """
        Resume virtual machines
        :param guest_name: the virtual machines you want to resume.
        :return: resume successfully, return True, else, return False.
        """
        cmd = f"PowerShell Resume-VM -Name {guest_name}"
        ret, _ = self.ssh.runcmd(cmd)
        if not ret and self.guest_info(guest_name)["guest_state"] == 2:
            logger.info("Succeeded to resume hyperv guest")
            return True
        else:
            logger.error("Failed to resume hyperv guest")
            return False

    def guest_uuid_change(self, guid, guest_name):
        """
        Change guid for guest
        :param guid: the guid for guest
        :param guest_name: the name for the guest
        :return: change guid successfully, return True, else, return False.
        """
        create_function_cmd = r"PowerShell (Invoke-WebRequest http://10.73.131.85/ci/hyperv/New-VMBIOSGUID.ps1 -OutFile ./New-VMBIOSGUID.ps1)"
        ret, _ = self.ssh.runcmd(create_function_cmd)
        if ret:
            logger.error("Failed to create function")
            return False

        import_module_cmd = r"Import-Module ./New-VMBIOSGUID.ps1 -Force"
        set_ignore_verfiy_cmd = r"$ConfirmPreference = 'None'"
        change_guid_cmd = f'PowerShell -Command "{set_ignore_verfiy_cmd}; {import_module_cmd}; New-VMBIOSGUID -VM {guest_name} -NewID {guid}"'
        ret, _ = self.ssh.runcmd(change_guid_cmd)
        if not ret:
            logger.info("Succeeded to change hypervisor guid")
            return True
        else:
            logger.error("Failed to change hypervisor guid")
            return False
