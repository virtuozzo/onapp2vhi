import logging
import logging.handlers
import os
import re
import sys
from os.path import join
import time

from datetime import datetime
from colorlog import ColoredFormatter

LOG_PATH = ""


def setup_logger(log_output_path):
    """Return a logger with a default ColoredFormatter."""
    global LOG_PATH
    formatter = ColoredFormatter(
        "%(log_color)s[%(asctime)s] %(levelname)-8s%(reset)s %(log_color)s%(message)s",
        datefmt=None,
        reset=True,
        log_colors={'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red'}
    )

    # By default, we are using INFO level
    set_log_lvl = logging.INFO
    # If you want to watch DEBUG logs please type in the console: [root@cp ~]# export loglevel=debug
    _env_log_lvl = os.environ.get('loglevel')
    if _env_log_lvl:
        _env_log_lvl = _env_log_lvl.lower()
    if _env_log_lvl == 'debug':
        set_log_lvl = logging.DEBUG
    elif _env_log_lvl in ('warning', 'warn'):
        set_log_lvl = logging.WARNING
    elif _env_log_lvl == 'error':
        set_log_lvl = logging.ERROR
    _pid = os.getpid()

    LOG_PATH = log_output_path
    _log_folder_path = log_output_path
    _migration_folder = 'migration_logs'

    _file_name = f'{_migration_folder}/migration_{_pid}.log'
    path = join(_log_folder_path, _file_name)
    _dir_path = join(_log_folder_path, _migration_folder)

    if len(sys.argv) > 1 and all(arg not in ['list-onapp-vms', 'list-onapp-users'] for arg in sys.argv):

        #only create folder when condition is true
        logger = logging.getLogger('migrate')
        if not os.path.exists(_dir_path):
            os.makedirs(_dir_path)

        logging.basicConfig(filename=path,
                            filemode='a',
                            format='[%(asctime)s,%(msecs)d] [%(levelname)s] %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.DEBUG)
    else:
        logger = logging.getLogger('table_output')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    logger.setLevel(set_log_lvl)


def get_logger():

    if len(sys.argv) > 1 and all(arg not in ['list-onapp-vms', 'list-onapp-users'] for arg in sys.argv):
        logger = logging.getLogger("migrate")
    else:
        logger = logging.getLogger("table_output")

    return logger


def hide_password(msg):
    """
    Hide password in logs
    :param msg: "Password: 123456"
    :return: "Password is hidden"
    """
    pattern1 = r"(?<=password=[\"'])(.*?)(?=[\"'])"
    pattern2 = r"(?<=password\":[\"'])(.*?)(?=[\"'])"
    pattern3 = r"(?<=password: [\"'])(.*?)(?=[\"'])"

    pattern_all = re.compile(
        f"{pattern1}|{pattern2}|{pattern3}", flags=re.IGNORECASE
    )
    try:
        new_msg = re.sub(pattern_all, "*hidden*", msg)
    except TypeError:
        new_msg = msg
    return new_msg


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
        self._logger = get_logger()

    @staticmethod
    def _today_time():
        return datetime.now().strftime('%d.%m.%Y')

    @staticmethod
    def _human_time():
        return time.strftime('%H:%M:%S')

    @property
    def _log_time(self):
        return f'[{self._today_time()} | {self._human_time()}]\n'

    def debug(self, msg: str, separator=False):
        msg = hide_password(msg)
        if separator:
            self._logger.debug('')
            self._logger.debug('- - - '*15)
        self._logger.debug(msg)

    def info(self, msg: str, separator=False, header=False):
        msg = hide_password(msg)
        if separator:
            self._logger.info('')
            self._logger.info('- - - ' * 15)
            self._logger.info(msg)
            return
        if header:
            self._logger.info('')
            self._logger.info('- - - ' * 15)
            self._logger.info(msg)
            self._logger.info('- - - ' * 15)
            return

        self._logger.info(msg)

    def error(self, msg: str):
        msg = hide_password(msg)
        self._logger.error('#' * 50)
        self._logger.error(msg)
        self._logger.error('#' * 50)

    def warn(self, msg: str):
        msg = hide_password(msg)
        self._logger.warning('#' * 50)
        self._logger.warning(msg)
        self._logger.warning('#' * 50)

    def write_log(self, file_path: str, msg: str):
        """
        Write logs into file
        :param file_path: /home/user/project/file.txt
        :param msg: "Message to be written in the file"
        :return:
        """
        _folder_2 = '/'.join(file_path.split('/')[:-1])
        _path = join(LOG_PATH, _folder_2)
        if not os.path.exists(_path):
            os.mkdir(_path)
            self._logger.warning('#' * 50)
            self._logger.warning(f'Creating folder to store logs "{_path}"')

        _log_file = f'{LOG_PATH}/{file_path}.log'
        with open(_log_file, 'a+') as _file:
            self._logger.warning('#' * 50)
            self._logger.warning(f'Info has been saved in "{_log_file}"')
            _file.write(self._log_time)
            _file.write(msg + '\n\n')
