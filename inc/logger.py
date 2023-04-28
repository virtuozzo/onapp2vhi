import logging
import logging.handlers
import os
import sys
from os.path import join, dirname, abspath
import time

from datetime import datetime
from colorlog import ColoredFormatter


def setup_logger():
    """Return a logger with a default ColoredFormatter."""
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
    logger = logging.getLogger('example')
    _time = f"{datetime.now().strftime('%d_%m_%Y')}_{time.strftime('%H_%M_%S')}"
    _migration_folder = 'migration_logs'
    _file_name = f'{_migration_folder}/full_log_{_time}.log'
    _root_folder = dirname(dirname(abspath(__file__)))
    path = join(_root_folder, _file_name)
    _dir_path = join(_root_folder, _migration_folder)
    if not os.path.exists(_dir_path):
        os.mkdir(_dir_path)

    if sys.argv[1] not in ('list_onapp_vms', 'list_onapp_users'):
        logging.basicConfig(filename=path,
                            filemode='a',
                            format='[%(asctime)s,%(msecs)d] [%(levelname)s] %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(set_log_lvl)
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
        return f'[{self._today_time()} | {self._human_time()}]\n'

    def debug(self, msg: str, separator=False):
        if separator:
            self._logger.debug('')
            self._logger.debug('- - - '*15)
        self._logger.debug(msg)

    def info(self, msg: str, separator=False, header=False):
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
        self._logger.error('#' * 50)
        self._logger.error(msg)
        self._logger.error('#' * 50)

    def warn(self, msg: str):
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
        _folder_1 = '/'.join(file_path.split('/')[:-2])
        for path in [_folder_1, _folder_2]:
            if not os.path.exists(path):
                os.mkdir(path)
                self._logger.warning('#' * 50)
                self._logger.warning(f'Creating folder to store logs "{path}"')
                continue

        _log_file = f'{file_path}.log'
        with open(_log_file, 'a+') as _file:
            self._logger.warning('#' * 50)
            self._logger.warning(f'Info has been saved in "{_log_file}"')
            _file.write(self._log_time)
            _file.write(msg + '\n\n')


logs = OnAppVHILogger()
