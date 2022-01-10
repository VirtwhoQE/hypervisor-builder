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
    """Kubevirt REST Api interface class"""
    def __init__(self, endpoint, token, internal_debug=None):
        """
        :param endpoint: endpoint for the kubevirt server
        :param token: token for the kubevirt server
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

    def _request(self, path):
        """
        Send a get request to the server.
        :param path: path for the url
        :return: return data for the result
        """
        header_params = {}
        header_params['Accept'] = 'application/json'
        header_params['Content-Type'] = 'application/json'
        header_params['Authorization'] = self.token
        url = self.endpoint + path

        try:
            timeout = Timeout(connect=_TIMEOUT, read=_TIMEOUT)
            r = self._pool_manager.request(
                "GET",
                url,
                fields=None,
                preload_content=True,
                headers=header_params,
                timeout=timeout
            )
            if self.internal_debug:
                logger.debug(f'GET method The request url sent: {url}')
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

        if not 200 <= r.status <= 299:
            raise FailException("Unknown Error")

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

    def get_vms(self):
        """
        Returns the params for the virtual manager.
        :return:
        """
        return self._request('/apis/kubevirt.io/' + self._kubevirt_version() + '/virtualmachineinstances')
