import json
import time

from . import ahv_constants
from hypervisor import logger
from hypervisor import FailException
from requests import Session
from requests.exceptions import ConnectionError, ReadTimeout


class AHVApi(object):
    """ AHV REST Api interface class"""
    NO_RETRY_HTTP_CODES = [400, 404, 500, 502, 503]

    def __init__(self, server, username, password, port=ahv_constants.DEFAULT_PORT,
                 version=ahv_constants.VERSION_2, **kwargs):
        """
        Args:
            server (str) : the ip for the ahv server
            username (str): Username.
            password (str): Password for rest client.
            port (int): Port number for ssp.
            version (str): Interface version.
            kwargs(dict): Accepts following arguments:
                timeout(optional, int): Max seconds to wait before HTTP connection
                times-out. Default 30 seconds.
                retries (optional, int): Maximum number of retires. Default: 5.
                retry_interval (optional, int): Time to sleep between retry intervals.
                internal_debug (optional, bool): Detail log of the rest calls.
                Default: 5 seconds.
        """
        self._session = Session()
        self._timeout = kwargs.get('timeout', 30)
        self._retries = kwargs.get('retries', 5)
        self._retry_interval = kwargs.get('retry_interval', 30)
        self._version = version
        self._url = ahv_constants.SERVER_BASE_URIL.format(
            server=server, port=port, version=self._version)
        self._user = username
        self._password = password
        self._port = port
        self._internal_debug = kwargs.get('internal_debug', False)
        self._create_session(self._user, self._password)

    def _create_session(self, user=None, password=None):
        """
        Creates rest session.
        Args:
            user (str): Username.
            password (str): Password for rest session.
        Returns:
            None.
        """
        if user is None:
            user = self._user
        if password is None:
            password = self._password
        self._session.auth = (user, password)

    def _make_url(self, uri, *args):
        """
        Creates base url.
        uri would always begin with a slash
        Args:
            uri (str): Uri.
            args (list): Args.
        Returns:
            url (str): Url with uri.
        """
        if not uri.startswith("/"):
            uri = f'/{uri}'
        url = f'{self._url}{uri}'
        for arg in args:
            url += f'{arg}'
        return url

    def _format_response(self, data):
        """
        Format the data based on the response's version.
        Args:
            data (dict): Data dictionary.
        Returns:
            formatted_data (dict): Formatted dictionary.
        """
        if 'entities' in data:
            return self._process_entities_list(data['entities'])
        else:
            return self._process_dict_response(data)

    def _process_dict_response(self, data):
        """
        Format the data when we only have a dictionary.
        Args:
            data (dict): Data dictionary.
        Returns:
            formatted_data (dict): Formatted data.
        """
        formatted_data = data
        if 'status' in data and 'metadata' in data:
            formatted_data = dict(data['status'], **data['metadata'])

        if 'resources' in formatted_data:
            if 'power_state' in formatted_data['resources']:
                formatted_data['power_state'] = \
                    formatted_data['resources']['power_state']
            if 'num_cpu_sockets' in formatted_data['resources']:
                formatted_data['num_cpu_sockets'] = \
                    formatted_data['resources']['num_cpu_sockets']

        return formatted_data

    def _process_entities_list(self, data):
        """
        Format data for the list of entities.
        Args:
            data (list): List of entities dictionary.
        Returns:
            formatted_data (dict): Formatted data after processing list fo entities.
        """
        formatted_data = data
        initial = True
        for entity in data:
            if 'status' in entity and 'metadata' in entity:
                if initial:
                    formatted_data = []
                    initial = False
                formatted_data.append(dict(entity['status'], **entity['metadata']))

        for ent_obj in formatted_data:
            if 'resources' in ent_obj:
                if 'nodes' in ent_obj['resources']:
                    nodes = ent_obj['resources']['nodes']
                    if 'hypervisor_server_list' in nodes:
                        ent_obj['hypervisor_types'] = []
                        for server in nodes['hypervisor_server_list']:
                            ent_obj['hypervisor_types'].append(server['type'])

            if 'kind' in ent_obj:
                if ent_obj['kind'] == 'cluster':
                    if 'uuid' in ent_obj:
                        ent_obj['cluster_uuid'] = ent_obj['uuid']

        return formatted_data

    def get(self, uri, *args, **kwargs):
        """
        Args are appended to the url as components.
        /arg1/arg2/arg3
        Send a get request with kwargs to the server.
        Args:
            uri (str): Uri.
            args (list): Args.
            kwargs (dict): Dictionary of params.
        Returns:
            Response (requests.Response): rsp.
        """
        url = self._make_url(uri, *args)
        return self._send('get', url, **kwargs)

    def post(self, uri, **kwargs):
        """
        Send a Post request to the server.
        Body can be either the dict or passed as kwargs
        headers is a dict.
        Args:
            uri (str): Uri.
            kwargs (dict): Dictionary of params.
        Returns:
            Response (requests.Response): rsp.
        """
        url = self._make_url(uri)
        return self._send('post', url, **kwargs)

    def make_rest_call(self, method, uri, *args, **kwargs):
        """This method calls the appropriate rest method based on the arguments.

        Args:
            method (str): HTTP method.
            uri (str): Relative_uri.
            args(any): Arguments.
            kwargs(dict): Key value pair for the additional args.

        Returns:
            rsp (dict): The response content loaded as a JSON.
        """
        func = getattr(self, method)
        return func(uri, *args, **kwargs)

    def _send(self, method, url, **kwargs):
        """This private method acting as proxy for all http methods.
        Args:
            method (str): The http method type.
            url (str): The URL to for the Request
            kwargs (dict): Keyword args to be passed to the requests call.
                retries (int): The retry count in case of HTTP errors.
                                             Except the codes in the list NO_RETRY_HTTP_CODES.

        Returns:
            Response (requests.Response): The response object.
        """
        kwargs['verify'] = kwargs.get('verify', False)
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self._timeout
        if 'json' in kwargs:
            kwargs['data'] = json.dumps(kwargs['json'])
            del kwargs['json']
        else:
            body = {}
            kwargs['data'] = json.dumps(body)

        content_dict = {'content-type': 'application/json'}
        kwargs.setdefault('headers', {})
        kwargs['headers'].update(content_dict)

        func = getattr(self._session, method)
        response = None

        retries = kwargs.pop("retries", None)
        retry_interval = kwargs.pop("retry_interval", self._retry_interval)
        retry_count = retries if retries else self._retries
        for ii in range(retry_count):
            try:
                response = func(url, **kwargs)
                if self._internal_debug:
                    logger.debug(f'{method.upper()} method The request url sent: {response.request.url}')
                    logger.debug(f'Response status: {response.status_code}')
                    logger.debug(f'Response: {json.dumps(response.json(), indent=4)}')

            except (ConnectionError, ReadTimeout) as e:
                logger.warning(f"Request failed with error: {e}")
                if ii != retry_count - 1:
                    time.sleep(retry_interval)
                continue
            finally:
                self._session.close()
            if response.ok:
                return response
            if response.status_code in [401, 403]:
                raise FailException(
                    f'HTTP Auth Failed {method} {url}. \n res: response: {response}'
                )
            elif response.status_code == 409:
                raise FailException(
                    f'HTTP conflict with the current state of '
                    f'the target resource {method} {url}. \n res: {response}'
                )
            elif response.status_code in self.NO_RETRY_HTTP_CODES:
                break
            if ii != retry_count - 1:
                time.sleep(retry_interval)

        if response is not None:
            msg = f'HTTP {method} {url} failed: '
            if hasattr(response, "text") and response.text:
                msg = "\n".join([msg, response.text]).encode('utf-8')
                logger.error(msg)
        else:
            logger.error(f"Failed to make the HTTP request ({method}, {url})")

    def get_common_ver_url_and_method(self, cmd_key):
        """
        Gets the correct cmd name based on its corresponding version.
        Args:
            cmd_key (str): Key name to search for in the command dict.
        Returns:
            (str, str) : Tuple of (command, rest_type).
        """
        return (
            ahv_constants.CMN_RST_CMD[cmd_key]['url'],
            ahv_constants.CMN_RST_CMD[cmd_key]['method']
        )

    def get_diff_ver_url_and_method(self, cmd_key, intf_version):
        """
        Gets the correct cmd name based on its corresponding version
        Args:
            cmd_key (str): Key name to search for in the command dict.
            intf_version (str): Interface version.
        Returns:
            (str, str) : Tuple of (command, rest_type).
        """
        return (
            ahv_constants.REST_CMD[intf_version][cmd_key]['url'],
            ahv_constants.REST_CMD[intf_version][cmd_key]['method']
        )

    def get_hosts_info(self):
        """
        Returns the list of host name.
        Args:
        Returns:
            host_name_list (list): list of host's name.
        """
        host_name_list = []
        (url, cmd_method) = self.get_diff_ver_url_and_method(
            cmd_key='list_hosts', intf_version=self._version)

        res = self.make_rest_call(method=cmd_method, uri=url)
        data = res.json()
        if 'entities' in data:
            for host_entity in data['entities']:
                if 'status' in host_entity and 'metadata' in host_entity:
                    # Check if a physical host, not a cluster.
                    if 'cpu_model' in host_entity['status']:
                        host_name_list.append(host_entity['metadata']['name'])
                elif 'name' in host_entity:
                    host_name_list.append(host_entity['name'])
                else:
                    logger.warning(
                        f"Cannot access the name for the host object: {host_entity}"
                    )
        return host_name_list

    def get_vm_by_name(self, guest_name, include_vm_disk_config=None, include_vm_nic_config=None):
        """
        Returns vm information
        Args:
            guest_name (string) : Vm name
            include_vm_disk_config (bool) : Whether to include Virtual Machine disk information
            include_vm_nic_config (bool) : Whether to include network information
        Returns:
            Vm info (dict)
        """
        (url, cmd_method) = self.get_diff_ver_url_and_method(
            cmd_key='list_vms', intf_version=self._version)
        url = f'{url}/?name={guest_name}'
        if include_vm_nic_config is not None:
            url += f'&include_vm_nic_config={include_vm_nic_config}'
        if include_vm_disk_config is not None:
            url += f'&include_vm_disk_config={include_vm_disk_config}'
        res = self.make_rest_call(method=cmd_method, uri=url)
        if res:
            data = res.json()
            return self._format_response(data)
        return None

    def get_vm_host_uuid_from_vm(self, vm_entity):
        """
        Get the host uuid from the vm_entity response
        Args:
            vm_entity (dict): Vm info.
        Returns:
            host uuid (str): Vm host uuid if found, none otherwise.
        """
        if 'resources' in vm_entity:
            if 'host_reference' in vm_entity['resources']:
                return vm_entity['resources']['host_reference']['uuid']
            else:
                logger.warning(
                    f"Did not find any host information for vm:{vm_entity['uuid']}"
                )
        elif 'host_uuid' in vm_entity:
            return vm_entity['host_uuid']
        else:
            # Vm is off therefore no host is assigned to it.
            logger.debug(
                f"Cannot get the host uuid of the vm:{vm_entity['uuid']}. "
                f"Perhaps the vm is powered off"
            )
        return None

    def get_vm(self, uuid):
        """
        Get details of a specific Virtual Machines.
        Args:
            uuid (str): Vm uuid.
        Return:
            data (dict): Vm information.
        """
        (url, cmd_method) = self.get_common_ver_url_and_method(cmd_key='get_vm')
        url = url.format(uuid=uuid)
        res = self.make_rest_call(method=cmd_method, uri=url)
        if res:
            data = res.json()
            return self._format_response(data)
        return None

    def get_host(self, uuid):
        """
        Returns host information
        Args:
            uuid (str): Host uuid.
        Return:
            data (dict): Host information.
        """
        (url, cmd_method) = self.get_common_ver_url_and_method(cmd_key='get_host')
        url = url.format(uuid=uuid)
        res = self.make_rest_call(method=cmd_method, uri=url)
        if res:
            data = res.json()
            return self._format_response(data)
        else:
            return None

    def get_host_cluster_name(self, cluster_uuid):
        """
        Returns host's cluster name.
        Args:
            cluster_uuid: Cluster uuid.
        Returns:
            host's cluster name.
        """
        (url, cmd_method) = self.get_diff_ver_url_and_method(
            cmd_key='list_clusters', intf_version=self._version)
        res = self.make_rest_call(method=cmd_method, uri=url)
        data = res.json()

        formatted_data = self._format_response(data)

        for cluster in formatted_data:
            if 'hypervisor_types' in cluster and 'cluster_uuid' in cluster:
                for hypevirsor_type in cluster['hypervisor_types']:
                    if cluster['cluster_uuid'] == cluster_uuid:
                        return cluster['name']
        return None

    def guest_search(self, guest_name):
        """
        Search the specific guest, return the expected attributes
        Args:
            guest_name (string) : name for the specific guest
        Returns:
            Vm info (dict): guest attributes, include guest_name, guest_uuid, guest_state,
            uuid, hostname, version, cpu and cluster.
        """
        guest_msgs = {}
        guest_vm = self.get_vm_by_name(guest_name, include_vm_nic_config=True)
        if len(guest_vm) > 0:
            for vm in guest_vm:
                guest_msgs = {
                    'guest_name': vm['name'],
                    'guest_uuid': vm['uuid'],
                    'guest_state': vm['power_state'],
                }
                if 'vm_nics' in vm:
                    for vm_nic in vm['vm_nics']:
                        guest_msgs['guest_ip'] = vm_nic['ip_address']
                host_uuid = self.get_vm_host_uuid_from_vm(vm)
                if host_uuid:
                    host = self.get_host(host_uuid)
                    if host:
                        guest_msgs['uuid'] = host['uuid']
                        guest_msgs['hostname'] = host['name']
                        guest_msgs['version'] = host['hypervisor_full_name']
                        guest_msgs['cpu'] = host['num_cpu_sockets']
                        cluster_uuid = host['cluster_uuid']
                        guest_msgs['cluster'] = self.get_host_cluster_name(cluster_uuid)
        return guest_msgs

    def guest_set_power_state(self, guest_name, state):
        """
        Set power state of a Virtual Machine.
        The UUID of this task object is returned as the response of this operation.
        This task can be monitored by using the /tasks/poll API.
        Args:
            guest_name (str): Vm name
            state (string): The desired power state transition, should be:
            ['ON', 'OFF', 'POWERCYCLE', 'RESET', 'PAUSE', 'SUSPEND',
            'RESUME', 'SAVE', 'ACPI_SHUTDOWN', 'ACPI_REBOOT']
        Return:
            data (dict): Vm information.
        """
        guest = self.get_vm_by_name(guest_name)
        if len(guest) == 1:
            uuid = guest[0]['uuid']
        (url, cmd_method) = self.get_common_ver_url_and_method(cmd_key='vm_set_power_state')
        url = url.format(uuid=uuid)
        body = {"transition": f"{state}"}
        logger.info(f"Set the power state '{state}' for the VM {guest_name}")
        res = self.make_rest_call(method=cmd_method, uri=url, json=body)
        if res:
            data = self._format_response(res.json())
            result = self.poll_task(data['task_uuid'])
            if 'completed_tasks_info' in result:
                result = result['completed_tasks_info']
                for task in result:
                    task_status = ''
                    if 'progress_status' in task:
                        if task['progress_status'] in ahv_constants.TASK_COMPLETE_MSG:
                            task_status = True
                        elif task['progress_status'] == 'Failed':
                            task_status = False
                            if 'meta_response' in task:
                                logger.error(task['meta_response']['error_detail'])
                        return task_status
        return False

    def guest_start(self, guest_name):
        """
        Power on virtual machines.
        :param guest_name: the virtual machines you want to power on.
        :return: the status of the action
        """
        return self.guest_set_power_state(guest_name, 'ON')

    def guest_stop(self, guest_name):
        """
        Power off virtual machines.
        :param guest_name: the virtual machines you want to power off.
        :return: the status of the action
        """
        return self.guest_set_power_state(guest_name, 'OFF')

    def guest_suspend(self, guest_name):
        """
        Suspend virtual machines.
        :param guest_name: the virtual machines you want to suspend.
        :return: the status of the action
        """
        return self.guest_set_power_state(guest_name, 'SUSPEND')

    def guest_resume(self, guest_name):
        """
        Resume virtual machines
        :param guest_name: the virtual machines you want to resume.
        :return: the status of the action
        """
        return self.guest_set_power_state(guest_name, 'RESUME')

    def poll_task(self, task_uuid, timeout_interval=60):
        """
        Poll a task to check if its ready.
        :param task_uuid: The UUID of task to be polled for completion.
        :param timeout_interval: The maximum amount of time to wait, in seconds,
        before the poll request times out.
        :return: completed_tasks_info
        """
        (url, cmd_method) = self.get_common_ver_url_and_method(cmd_key='poll_task')
        body = {"completed_tasks": [f'{task_uuid}'], "timeout_interval": f'{timeout_interval}'}
        res = self.make_rest_call(method=cmd_method, uri=url, json=body)
        if res:
            data = res.json()
            return self._format_response(data)
        return None

    def guest_del(self, guest_name):
        """
        Delete a Virtual Machine.
        The UUID of this task object is returned as the response of this operation.
        This task can be monitored by using the /tasks/poll API.
        :param guest_name: the virtual machines you want to delete.
        :return:
        """
        pass

    def guest_add(self, guest_name):
        """
        Create a Virtual Machine with specified configuration.
        The UUID of this task object is returned as the response of this operation.
        This task can be monitored by using the /tasks/poll API.
        :param guest_name:
        :return:
        """
        pass
