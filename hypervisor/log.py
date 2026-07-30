import logging
import os
import tempfile
import time

# Log to /var/log/hypervisor-builder — writable on both traditional and
# bootc image-mode systems (/var is always read-write).  Falls back to
# a temp directory when not running as root (dev machines, CI containers).
#
# The previous default placed logs next to the installed package in
# site-packages/, which is read-only on imagemode.
_LOG_DIR = "/var/log/hypervisor-builder"


def _ensure_log_dir():
    """Create and return a writable log directory."""
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        return _LOG_DIR
    except OSError:
        fallback = os.path.join(tempfile.gettempdir(), "hypervisor-builder")
        os.makedirs(fallback, exist_ok=True)
        return fallback


class Logger:
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
        """
        self.logger = logging.getLogger(logger)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        self.log_path = _ensure_log_dir()
        self.log_name = os.path.join(
            self.log_path, "{}.log".format(time.strftime("%Y_%m_%d"))
        )
        self.formatter = logging.Formatter(
            "[%(asctime)s] - [%(filename)s] - %(levelname)s: %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

        fh = logging.FileHandler(self.log_name, "a", encoding="utf-8")
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
