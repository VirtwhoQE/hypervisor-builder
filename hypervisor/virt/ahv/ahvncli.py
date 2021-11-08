from hypervisor import FailException
from hypervisor import logger
from hypervisor.ssh import SSHConnect


class AHVnCLI:
    def __init__(self, server, ssh_user, ssh_pwd):
        """
        Collect AHV information, provide Guest add/delete/start/stop/suspend/resume functions
        via ncli Command line following 'https://portal.nutanix.com/page/documents/details?
        targetId=Command-Ref-AOS-v6_0:man-ncli-c.html'
        :param server: the ip for the AHV server
        :param ssh_user: the ssh user for the AHV server
        :param ssh_pwd: the ssh password for the AHV server
        """
        self.server = server
        self.ssh_user = ssh_user
        self.ssh_pwd = ssh_pwd
        self.ssh = SSHConnect(self.server, user=self.ssh_user, pwd=self.ssh_pwd)

    def get_ncli_info(self, cmd, value):
        """
        Get the info from AHV
        :param cmd:
        :param value: the value you want to get from the result
        :return: the value you want to get
        """
        cmd = f"/home/nutanix/prism/cli/ncli {cmd} |grep '^    {value}'"
        ret, output = self.ssh.runcmd(cmd)
        for line in output.split('\n'):
            if not ret and value in line:
                result = line.split(':')[1].strip()
                logger.info(f"Succeeded to get {value}: {result}")
                return result
        else:
            logger.info(f"Failed to get {value}")
            return None

    def guest_search(self, guest_name):
        """
        Search the specific guest, return the expected attributes
        :param guest_name: name for the specific guest
        :param host_ip: the ip for the AHV host
        :param host_user: the ssh username for the AHV host
        :param host_pwd: the ssh password for the AHV host
        :return: guest attributes, exclude guest_name, guest_ip, guest_uuid ...
        """
        guest_msgs = {
            'guest_name': guest_name,
            'guest_ip': self.get_ncli_info(
                "virtualmachine list name=rhel84_guest", 'VM IP Addresses'),
            'guest_uuid': self.get_ncli_info("virtualmachine list name=rhel84_guest", 'Uuid'),
            'guest_state': "",
            'ahv_uuid': self.get_ncli_info(
                "virtualmachine list name=rhel84_guest", 'Hypervisor Host Uuid'),
            'ahv_hwuuid': "",
            'ahv_hostname': self.get_ncli_info(
                "virtualmachine list name=rhel84_guest", 'Hypervisor Host Name'),
            'ahv_version': self.get_ncli_info("host list", 'Hypervisor Version'),
            'ahv_cpu': "",
            'cluster_name': self.get_ncli_info("cluster info", 'Cluster Name'),
        }
        return guest_msgs
