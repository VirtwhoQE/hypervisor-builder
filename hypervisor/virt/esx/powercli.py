import re
import json
from hypervisor.log import getLogger
from hypervisor.ssh import SSHConnect

logger = getLogger(__name__)


class PowerCLI():
    def __init__(self, server, admin_user, admin_passwd, ssh_user, ssh_passwd):
        self.server =  server
        self.admin_user = admin_user
        self.admin_passwd = admin_passwd 
        self.ssh_user = ssh_user 
        self.ssh_passwd = ssh_passwd 
        self.cert = ("powershell Connect-VIServer -Server {0} -Protocol https -User {1} -Password {2};".format(
            self.server,
            self.admin_user,
            self.admin_passwd)
        )
        self.ssh = SSHConnect(self.server, user=self.ssh_user, pwd=self.ssh_passwd)
        self.json = 'ConvertTo-Json -Depth 1'

    def _format(self, ret=0, stdout=None):
        stdout = re.findall(r'[[][\W\w]+[]]', stdout)[0]
        if ret == 0 and stdout is not None: 
            return json.loads(stdout)

    def info(self):
        mapping = {}
        ret, output = self.ssh.runcmd("{0} Get-VMHost | {1}".format(self.cert, self.json))
        logger.info(output)
        output = self._format(ret, output)
        for host in output:
            logger.info(host['Name'])

    def host_add():
        pass

    def host_del():
        pass

    def guest_add():
        pass

    def guest_del():
        pass

    def guest_start():
        pass

    def guest_stop():
        pass

    def guest_suspend():
        pass

    def guest_resume():
        pass


cli = PowerCLI('10.73.131.152', admin_user='administrator@vsphere.local', admin_passwd='Welcome1!', ssh_user='Administrator', ssh_passwd='Welcome1')
cli.info()
