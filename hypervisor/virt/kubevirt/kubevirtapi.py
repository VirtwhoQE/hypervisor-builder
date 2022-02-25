import json
import math
import ssl
import urllib3

from hypervisor import FailException
from hypervisor import logger
from six import PY3
from urllib3.util.timeout import Timeout

_TIMEOUT = 60


class KubevirtApi:
    """Kubevirt REST Api interface class following the document:
    http://kubevirt.io/api-reference/v0.44.3/operations.html"""
    def __init__(self, endpoint, token, internal_debug=None):
        """
        :param endpoint: endpoint for the kubevirt server
        :param token: token for the kubevirt server
        :param internal_debug: detail log of the rest calls.
        """
        self._pool_manager = urllib3.PoolManager(
            num_pools=4,
            maxsize=4,
            cert_reqs=ssl.CERT_NONE
        )
        self.endpoint = endpoint
        self.token = f"Bearer {token}"
        self.internal_debug=internal_debug

    def _kubevirt_version(self):
        """
        Return the kubevirt api version
        :return: Kubevirt api version
        """
        versions = self._request('/apis/kubevirt.io')
        return versions['preferredVersion']['version']

    def _request(self, path, method='GET', field=None):
        """
        Send a request to the server.
        :param path: path for the url
        :return: return data for the result
        """
        header_params = {}
        header_params['Authorization'] = self.token
        url = self.endpoint + path

        try:
            timeout = Timeout(connect=_TIMEOUT, read=_TIMEOUT)
            r = self._pool_manager.request(
                method,
                url,
                fields=field,
                preload_content=True,
                headers=header_params,
                timeout=timeout
            )
            if self.internal_debug:
                logger.debug(f'{method} method The request url sent: {url}')
                logger.debug(f'Response status: {r.status}')

        except urllib3.exceptions.SSLError as e:
            msg = f"{type(e).__name__}\n{str(e)}"
            raise FailException(msg)

        if PY3:
            data = r.data.decode('utf8')
        else:
            data = r.data
        if self.internal_debug:
            logger.debug(f'Response: {data}')

        if not 200 <= r.status <= 299 and not r.status == 202:
            raise FailException(f"Error: {r.data}")

        try:
            data = json.loads(data)
        except ValueError:
            data = r.data
        return data

    def get_nodes(self):
        """
        Get the params for the nodes
        :return: the params for the nodes
        """
        return self._request('/api/v1/nodes')

    def get_vminst(self):
        """
        Returns the params for the virtual manager instances by
        GET /apis/kubevirt.io/v1/virtualmachineinstances
        :return: the params for the virtual manager instances
        """
        path = '/apis/kubevirt.io/' + self._kubevirt_version() + '/virtualmachineinstances'
        return self._request(path)

    def get_vms(self):
        """
        Returns the params for the virtual managers by
        GET /apis/kubevirt.io/v1/virtualmachines
        :return:
        """
        path = '/apis/kubevirt.io/' + self._kubevirt_version() + '/virtualmachines'
        return self._request(path)

    def get_nodes_list(self):
        """
        Returns the list for the node name.
        :return: list of node's name.
        """
        hosts = []
        nodes = self.get_nodes()
        for node in nodes['items']:
            name = node['metadata']['name']
            hosts.append(name)
        logger.debug(f"node list: {hosts}")
        return hosts

    def parse_cpu(self, cpu):
        """
        Parse the cpu to normal value
        :param cpu: original value for the cpu
        :return: the cpu after the convert
        """
        if cpu.endswith('m'):
            cpu = int(math.floor(int(cpu[:-1]) / 1000))
        return str(cpu)

    def get_host_info(self, node_name):
        """
        Returns the messages for the host.
        :param node_name: the name for the specific node
        :return: return the host info include the host uuid, cpu, version and hostname
        """
        nodes = self.get_nodes()
        host_info = {}
        for node in nodes['items']:
            if node['metadata']['name'] == node_name:
                host_info['uuid'] = node['status']['nodeInfo']['machineID']
                host_info['cpu'] = self.parse_cpu(node['status']['allocatable']["cpu"])
                host_info['version'] = node['status']['nodeInfo']['kubeletVersion']
                for addr in node['status']['addresses']:
                    if addr['type'] == 'Hostname':
                        host_info['hostname'] = addr['address']
        logger.debug(f"host info: {host_info}")
        return host_info

    def get_vm_info(self, guest_name):
        """
        Returns the messages for the virtual manager.
        :param guest_name: the guest name for the specific guest
        :return: the guest messages for the virtual manger, include guest uuid, state,
        nodename, etc.
        """
        guest_info = {}
        vms_inst = self.get_vminst()
        for vm_inst in vms_inst['items']:
            if vm_inst['metadata']['name'] == guest_name:
                guest_info['guest_uuid'] = vm_inst['spec']['domain']['firmware']['uuid']
                guest_info['hostname'] = vm_inst['status']['nodeName']
                guest_info['guest_state'] = vm_inst['status']['phase']
        logger.debug(f"vm info: {guest_info}")
        return guest_info

    def get_vm_namespace(self, guest_name):
        """
        Get the namespace for the specific vm by GET apis/kubevirt.io/v1/virtualmachines
        :param guest_name:
        :return:
        """
        namespace = ''
        vms = self.get_vms()
        for vm in vms['items']:
            if vm['metadata']['name'] == guest_name:
                namespace = vm['metadata']['namespace']
        return namespace

    def guest_search(self, guest_name, guest_port):
        """
        Search the specific guest, return the expected attributes
        Args:
            guest_name (string) : name for the specific guest
            guest_port (int) : port for the specific guest
        Returns:
            Vm info (dict): guest attributes, include guest_name, guest_uuid, guest_state,
            uuid, hostname, version, cpu, etc.
        """
        guest_msgs = {}
        guest_msgs.update(self.get_vm_info(guest_name))
        if 'hostname' in guest_msgs:
            guest_msgs['guest_ip'] = f"{guest_msgs['hostname']}:{guest_port}"
            guest_msgs.update(self.get_host_info(guest_msgs['hostname']))
        return guest_msgs

    def guest_set_power_state(self, guest_name, state):
        """
        Set power state of a Virtual Machine.
        :param guest_name: Vm name
        :param state: The desired power state transition, should be:
            ['start', 'stop', 'restart', 'pause', 'unpause', 'freeze', 'unfreeze']
        :return:
        """
        namespace = self.get_vm_namespace(guest_name)
        path = '/apis/subresources.kubevirt.io/' + self._kubevirt_version() + \
               f'/namespaces/{namespace}/virtualmachines/{guest_name}/{state}'
        return self._request(path, 'PUT')

    def guest_start(self, guest_name):
        """
        Power on virtual machines.
        :param guest_name: the virtual machines you want to power on.
        :return:
        """
        return self.guest_set_power_state(guest_name, 'start')

    def guest_stop(self, guest_name):
        """
        Power off virtual machines.
        :param guest_name: the virtual machines you want to power off.
        :return:
        """
        return self.guest_set_power_state(guest_name, 'stop')
