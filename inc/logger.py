import logging
import os
import time

from datetime import datetime
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

    @staticmethod
    def _today_time():
        return datetime.now().strftime('%d.%m.%Y')

    @staticmethod
    def _human_time():
        return time.strftime('%H:%M:%S')

    @property
    def _log_time(self):
        return '[{} | {}]\n'.format(self._today_time(), self._human_time())

    def info(self, msg, separator=False):
        if separator:
            self._logger.info('- - - '*15)
        self._logger.info("{msg}".format(msg=msg))

    def error(self, msg, separator=False):
        self._logger.error('#' * 50)
        self._logger.error("{msg}".format(msg=msg))
        self._logger.error('#' * 50)

    def warn(self, msg, separator=False):
        self._logger.warning('#' * 50)
        self._logger.warning("{msg}".format(msg=msg))
        self._logger.warning('#' * 50)

    def write_log(self, file_path, msg, new_file=False):
        """
        Write logs into file
        :param file_path: /home/user/project/file.txt
        :param msg: "Message to be written in the file"
        :param new_file: bool
        :return:
        """
        _log_file = '{}.log'.format(file_path)
        if new_file:
            if os.path.exists(_log_file):
                self._logger.warning('#' * 50)
                self._logger.warning('Removing old log file "{}"'.format(_log_file))
                self._logger.warning('#' * 50)
                os.remove(_log_file)

        _folder = '/'.join(file_path.split('/')[:-1])
        if not os.path.exists(_folder):
            os.mkdir(_folder)
            self._logger.warning('#' * 50)
            self._logger.warning('Creating folder to store logs "{}"'.format(_folder))
        with open(_log_file, 'a+') as _file:
            self._logger.warning('#' * 50)
            self._logger.warning('Info has been saved in "{}"'.format(_log_file))
            _file.write(self._log_time)
            _file.write(msg + '\n\n')


logs = OnAppVHILogger()
