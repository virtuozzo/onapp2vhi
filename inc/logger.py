import logging
from colorlog import ColoredFormatter


def setup_logger():
    """Return a logger with a default ColoredFormatter."""
    formatter = ColoredFormatter(
        "%(log_color)s[%(asctime)s] %(levelname)-8s%(reset)s %(log_color)s%(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red',
        }
    )

    logger = logging.getLogger('example')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger


class OnAppVHILogger:
    """
    This module is use for showing logs in console
    You just need to specify what lvl of logs you need and as input data give string message
    INPUT:
    Logger().info("This is test message")
    OUTPUT:
    [2021-02-09 13:25:06,248] INFO     GET - https://www.google.com/
    """
    def __init__(self):
        self._logger = setup_logger()

    def info(self, msg, separator=False):
        if separator:
            self._logger.info('- - - '*15)
        self._logger.info("{msg}".format(msg=msg))

    def error(self, msg, separator=False):
        if separator:
            self._logger.info('- - - '*15)
        self._logger.error("{msg}".format(msg=msg))

    def warn(self, msg, separator=False):
        if separator:
            self._logger.info('- - - '*15)
        self._logger.warning("{msg}".format(msg=msg))


logs = OnAppVHILogger()
