from hypervisor.log import getLogger


logger = getLogger(__name__)


class FailException(BaseException):
    def __init__(self, error_message):
        logger.error(error_message)
