import os
import time
import logging


class Logger():
    """
    Usage:
        from hypervisor import log
        logger = log.getLogger(__name__)
        logger.info("abc")
        logger.debug("abc")
        logger.error("abc")
        logger.warning("abc")
    """
 
    def __init__(self, logger=None):
        """
        The log message will output to file and console.
        Define the log path, log file, log level, log formatter.
        The default log directory is logs.
        """
        self.logger = logging.getLogger(logger)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        self.log_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            'logs')
        if not os.path.exists(self.log_path):os.mkdir(self.log_path)
        self.log_name = os.path.join(self.log_path, '%s.log' % time.strftime('%Y_%m_%d'))
        self.formatter = logging.Formatter(
            '[%(asctime)s] - [%(filename)s] - %(levelname)s: %(message)s',
            '%Y-%m-%d %H:%M:%S'
        )

        fh = logging.FileHandler(self.log_name, 'a', encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(self.formatter)
        self.logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(self.formatter)
        self.logger.addHandler(ch)

        fh.close()
        ch.close()

    def getlog(self):
        return self.logger

def getLogger(name=None):
    """
    This method does the setup necessary to create 
    and connect the main logger instance.
    """
    return Logger(name).getlog()
