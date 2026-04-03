from hypervisor.log import getLogger


logger = getLogger(__name__)


class FailException(Exception):
    def __init__(self, error_message):
        logger.error(error_message)
