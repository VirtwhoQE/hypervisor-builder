import requests
import json
from hypervisor import logger


# Because the esxapi is not stable, so we use the ssh and PowerCLI to control the esx host
# Now this file is unused, but we will use it in the future
class Esxapi:
    def __init__(
        self,
        server,
        user,
        passwd,
    ):
        """
        Collect vcenter information, provide Host add/delete and
        Guest add/delete/start/stop/suspend/resume functions
        via ESXi official API
        """
        self.server = server
        self.user = user
        self.passwd = passwd
        self.timeout = 5
        self.session_id = requests.post(
            url=self.server + r"/api/session", auth=(user, passwd), timeout=self.timeout
        )

    def _format(self, response):
        return json.loads(response.text)

    def info(self):
        """
        Get the VMhost info
        :return: the VMHosts info
        """
        header = {"vmware-api-session-id": self.session_id}

        response = requests.get(
            url=self.server + r"/api/vcenter/host", headers=header, timeout=self.timeout
        )

        output = self._format(response)

        for host in output:
            logger.info(f"Get ESXi Host: {host['Name']}")

        return output

    def guest_add(self):
        """
        Create a new virtual machine.
        :param host: the host on which you want to create the new virtual machine.
        :param host_ssh_user: the ssh username for the host
        :param host_ssh_pwd: the ssh password for the host
        :param guest_name: the name for the new virtual machine
        :param image_path: the path for the guest image which from the remote web
        :return: create successfully, return True, else, return False
        """
        pass

    def guest_exist(self, guest_name):
        """
        Check if the esx guest exists
        :param guest_name: the name for the guest
        :return: guest exists, return True, else, return False.
        """
        # https://developer.vmware.com/apis/vsphere-automation/latest/vcenter/vcenter/VM/
        header = {"vmware-api-session-id": self.session_id}

        response = requests.get(
            url=self.server + r"/api/vcenter/vm/" + guest_name,
            headers=header,
            timeout=self.timeout,
        )

        if response.status != 200:
            return False

        return True

    def guest_search(self, guest_name, uuid_info=False):
        """
        Search the specific guest, return the expected attributes
        :param guest_name: name for the specific guest
        :param uuid_info: if you need the uuid_info: guest_uuid, esx_uuid, esx_hwuuid
        :return: guest attributes, exclude guest_name, guest_ip, guest_uuid ...
                 guest_state: guest_poweron:1, guest_poweroff:0, guest_Suspended:2
                 esx_state: host_poweron:1, host_poweroff:0
        """

        header = {"vmware-api-session-id": self.session_id}

        # https://developer.vmware.com/apis/vsphere-automation/latest/vcenter/vcenter/VM/
        response = requests.get(
            url=self.server + r"/api/vcenter/vm/" + guest_name,
            headers=header,
            timeout=self.timeout,
        )
        base_output = self._format(response)

        # https://developer.vmware.com/apis/vsphere-automation/latest/vcenter/api/vcenter/vm/vm/guest/identity/get/
        response = requests.get(
            url=self.server + r"/api/vcenter/vm/" + guest_name + r"/guest/identity",
            headers=header,
            timeout=self.timeout,
        )
        id_output = self._format(response)

        # host_name = id_output["host_name"]

        guest_msgs = {
            "guest_name": base_output["name"],
            "guest_state": base_output["power_state"],
            "guest_ip": id_output["ip_address"],
            "guest_cpu": base_output["cpu"]["count"],
            # "esx_ip": output["VMHost"]["Name"],
            "esx_hostname": id_output["host_name"],
            # "esx_version": output["VMHost"]["Version"],
            # "esx_state": output["VMHost"]["PowerState"],
            # "esx_cpu": str(output["VMHost"]["NumCpu"]),
            # "esx_cluster": output["VMHost"]["Parent"],
        }
        # if uuid_info:
        # guest_msgs["guest_uuid"] = self.guest_uuid(guest_name)
        # guest_msgs["esx_uuid"] = self.host_uuid(host_name)
        # guest_msgs["esx_hwuuid"] = self.host_hwuuid(host_name)
        return guest_msgs

    def guest_start(self, guest_name):
        """
        Power on virtual machines.
        :param guest_name: the virtual machines you want to power on.
        :return: power on successfully, return True, else, return False.
        """
        # https://developer.vmware.com/apis/vsphere-automation/latest/vcenter/vm/guest.power/
        header = {"vmware-api-session-id": self.session_id}

        response = requests.get(
            url=self.server + r"/api/vcenter/vm/" + guest_name + r"/power?action=start",
            headers=header,
            timeout=self.timeout,
        )

        if response.status_code == 204:
            logger.info("Succeeded to start vcenter guest")
            return True
        else:
            logger.error("Failed to start vcenter guest")
            return False

    def guest_stop(self, guest_name):
        # https://developer.vmware.com/apis/vsphere-automation/latest/vcenter/vm/guest.power/
        header = {"vmware-api-session-id": self.session_id}

        response = requests.get(
            url=self.server + r"/api/vcenter/vm/" + guest_name + r"/power?action=stop",
            headers=header,
            timeout=self.timeout,
        )

        if response.status_code == 204:
            logger.info("Succeeded to stop vcenter guest")
            return True
        else:
            logger.error("Failed to stop vcenter guest")
            return False

    def guest_suspend(self, guest_name):
        """
        Suspend virtual machines.
        :param guest_name: the virtual machines you want to suspend.
        :return: suspend successfully, return True, else, return False.
        """
        # https://developer.vmware.com/apis/vsphere-automation/latest/vcenter/vm/guest.power/
        header = {"vmware-api-session-id": self.session_id}

        response = requests.get(
            url=self.server
            + r"/api/vcenter/vm/"
            + guest_name
            + r"/power?action=suspend",
            headers=header,
            timeout=self.timeout,
        )

        if response.status_code == 204:
            logger.info("Succeeded to suspend vcenter guest")
            return True
        else:
            logger.error("Failed to suspend vcenter guest")
            return False

    def guest_resume(self, guest_name):
        """
        Resume virtual machines
        :param guest_name: the virtual machines you want to resume.
        :return: resume successfully, return True, else, return False.
        """
        # https://developer.vmware.com/apis/vsphere-automation/latest/vcenter/vm/guest.power/
        header = {"vmware-api-session-id": self.session_id}

        response = requests.get(
            url=self.server + r"/api/vcenter/vm/" + guest_name + r"/power?action=start",
            headers=header,
            timeout=self.timeout,
        )

        if response.status_code == 204:
            logger.info("Succeeded to resume vcenter guest")
            return True
        else:
            logger.error("Failed to resume vcenter guest")
            return False

    def guest_uuid(self):
        pass

    # https://developer.vmware.com/apis/vsphere-automation/latest/esx/api/esx/software/get/
    def host_uuid(self):
        pass

    def host_hwuuid(self):
        pass

    def host_start(self):
        pass

    def host_stop(self):
        pass

    def host_restart(self):
        pass

    def host_name_get(self):
        pass

    def host_name_set(self):
        pass

    def cluster_name_set(self):
        pass
