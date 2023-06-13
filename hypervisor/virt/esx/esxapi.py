import requests
import json
from hypervisor import logger
from hypervisor.ssh import SSHConnect

class Esxapi:
    def __init__(
        self,
        server,
        user,
        passwd,):
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
            url=self.server+r'/api/session',
            auth=(user,passwd),
            timeout=self.timeout
        )

    def _format(self, response):
        return json.loads(response.text)

    def info(self):
        """
        Get the VMhost info
        :return: the VMHosts info
        """
        header = {
            "vmware-api-session-id": self.session_id
        }
        
        response = requests.get(
            url=self.server+r'/api/vcenter/host',
            headers=header,
            timeout=self.timeout
        )
        
        output = self._format(response)
        
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
        :param image_path: the path for the guest image which from the remote web
        :return: create successfully, return True, else, return False
        """
        header = {
            "name": guest_name,
            
        }
    
    def guest_exist(self, guest_name):
        """
        Check if the esx guest exists
        :param guest_name: the name for the guest
        :return: guest exists, return True, else, return False.
        """
        header = {
            "vmware-api-session-id": self.session_id
        }
        
        response = requests.get(
            url=self.server+r'/api/vcenter/vm/'+guest_name,
            headers=header,
            timeout=self.timeout
        )
        
        if response.status!=200:
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
        
        header = {
            "vmware-api-session-id": self.session_id
        }
        
        response = requests.get(
            url=self.server+r'/api/vcenter/vm/'+guest_name,
            headers=header,
            timeout=self.timeout
        )
        
        output = self._format(response)
        