SERVER_BASE_URIL = 'https://{server}:{port}/api/nutanix/{version}'
AHV_HYPERVIRSOR = ['kKvm', 'AHV', 'ahv', 'kvm']
TASK_COMPLETE_MSG = ['SUCCEEDED', 'Succeeded']
DEFAULT_PORT = 9440
VERSION_2 = 'v2.0'
VERSION_3 = 'v3'

CMN_RST_CMD = {
    'get_vm': {'url': '/vms/{uuid}', 'method': 'get'},
    'get_host': {'url': '/hosts/{uuid}', 'method': 'get'},
    'get_tasks': {'url': '/tasks/list', 'method': 'post'},
    'get_task': {'url': '/tasks/{uuid}', 'method': 'get'},
    'poll_task': {'url': '/tasks/poll', 'method': 'post'},
    'create_vm': {'url': 'vms', 'method': 'post'},
    'delete_vm': {'url': '/vms/{uuid}', 'method': 'delete'},
    'vm_set_power_state': {'url': '/vms/{uuid}/set_power_state', 'method': 'post'},
}

REST_CMD = {
    VERSION_2: {
        'list_vms': {'url': '/vms', 'method': 'get'},
        'list_hosts': {'url': '/hosts', 'method': 'get'},
        'list_clusters': {'url': '/clusters', 'method': 'get'},
    },
    VERSION_3: {
        'list_vms': {'url': '/vms/list', 'method': 'post'},
        'list_hosts': {'url': '/hosts/list', 'method': 'post'},
        'list_clusters': {'url': '/clusters/list', 'method': 'post'},
    },
}
