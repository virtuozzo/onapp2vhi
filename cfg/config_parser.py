import os
from os.path import join, dirname, abspath
from configparser import ConfigParser
from inc.logger import logs
from typing import Dict


class CP:
    VHI = "vhi"
    OnApp = "onapp"


class AttributeDict(dict):
    def __getattr__(self, key):
        if key not in self:
            raise AttributeError(key)
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


class OnAppVhiCP:
    """
    Parsing config.cfg file to get credentials to different resources
    """
    _file_name = 'config.cfg'
    path = join(dirname(abspath(__file__)), _file_name)
    err_mgs = (f'Config file does NOT exist: {path}\nPlease create file with name '
               f'"{_file_name}" and provide properties as in "config-example.cfg" file')
    if not os.path.isfile(path):
        logs.error(err_mgs)
        exit(1)

    def __init__(self):
        self._config = ConfigParser(interpolation=None)
        self._config.read(self.path)
        self.CP = CP.OnApp
        self.VHI = CP.VHI
        self._KEY = 'key'
        self._cloud = ''

    def get_config(self, cp_type=None):
        """
        load config by cp_type
        """
        _config = {}
        if cp_type:
            for section in self._config.sections():
                _config[section] = {key: self._config[section][key] for key in self._config[section]}
            _config = _config[cp_type]
            return AttributeDict(**_config)
        return {"error: CP type is not set"}

    @property
    def on_app_cp(self) -> Dict:
        """
        :return: OnApp CP properties
        """
        return AttributeDict(
            {'url': self._config.get(self.CP, "cloud_url", raw=True),
             'email': self._config.get(self.CP, "email", raw=True),
             'host': self._config.get(self.CP, "host", raw=True),
             'api_key': self._config.get(self.CP, "api_key", raw=True),
             'cp_ssh_port': self._config.get(self.CP, "cp_ssh_port", raw=True),
             'hv_ssh_port': self._config.get(self.CP, "hv_ssh_port", raw=True)})

    @property
    def vhi_cp(self) -> Dict:
        """
        :return: VHI Cloud properties
        """
        return AttributeDict(
            {'url': self._config.get(self.VHI, "cloud_url", raw=True),
             'panel_url': self._config.get(self.VHI, "panel_url", raw=True),
             'api_path': self._config.get(self.VHI, "api_path", raw=True),
             'login': self._config.get(self.VHI, "login", raw=True),
             'admin_ui_pwd': self._config.get(self.VHI, "admin_ui_pwd", raw=True),
             'hv_ip': self._config.get(self.VHI, "hv_ip", raw=True),
             'cp_ip': self._config.get(self.VHI, "cp_ip", raw=True),
             'cloud_ssh_port': self._config.get(self.VHI, "vhi_ssh_port", raw=True),
             'hv_ssh_port': self._config.get(self.VHI, "vhi_ssh_port_hv", raw=True),
             'linux_image': self._config.get(self.VHI, "vhi_linux_image", raw=True),
             'windows_image': self._config.get(self.VHI, "vhi_windows_image", raw=True),
             'migration_network_id': self._config.get(self.VHI, "migration_network_id", raw=True),
             'domain_id': self._config.get(self.VHI, "vhi_domain_id", raw=True),
             'vinfra_domain': self._config.get(self.VHI, "vinfra_domain", raw=True),
             'vinfra_project': self._config.get(self.VHI, "vinfra_project", raw=True),
             'vinfra_domain_user': self._config.get(self.VHI, "vinfra_domain_user", raw=True),
             'vinfra_domain_pass': self._config.get(self.VHI, "vinfra_domain_pass", raw=True),
             'vinfra_user': self._config.get(self.VHI, "vinfra_user", raw=True),
             'vinfra_pass': self._config.get(self.VHI, "vinfra_pass", raw=True)})

    @property
    def ssh_key(self) -> str:
        return self._config.get(self._KEY, "ssh_key", raw=True)

    def set_new_value(self, section: str, option: str, value: str):
        """
        Set new value into config
        :param section: "VHI"
        :param option: "vinfra_project"
        :param value: "Default"
        :return:
        """
        self._config.set(section, option, value)
        with open(self.path, 'w+') as conf:
            self._config.write(conf)
        # Read conf file with new values
        import time
        time.sleep(1)
        self._config.read(self.path)
        time.sleep(1)

    def reset_auth(self):
        global VINFRA_AUTH
        VINFRA_AUTH = f"vinfra --vinfra-username='{self.vhi_cp['vinfra_user']}'" \
                      f" --vinfra-password='{self.vhi_cp['vinfra_pass']}'"
        return VINFRA_AUTH

    def reset_domain_auth(self):
        global DOMAIN_AUTH
        DOMAIN_AUTH = (f"vinfra --vinfra-username='{self.vhi_cp['vinfra_domain_user']}'"
                       f" --vinfra-password='{self.vhi_cp['vinfra_domain_pass']}'")
        return DOMAIN_AUTH


configs = OnAppVhiCP()
ONAPP_CREDS = configs.on_app_cp
VHI_CREDS = configs.vhi_cp
SSH_KEY = configs.ssh_key
VINFRA_AUTH = f"vinfra --vinfra-username='{VHI_CREDS['vinfra_user']}' --vinfra-password='{VHI_CREDS['vinfra_pass']}'"
ADMIN_AUTH = f"vinfra --vinfra-username='{VHI_CREDS['login']}' --vinfra-password='{VHI_CREDS['admin_ui_pwd']}'"
DOMAIN_AUTH = (f"vinfra --vinfra-username='{VHI_CREDS['vinfra_domain_user']}'"
               f" --vinfra-password='{VHI_CREDS['vinfra_domain_pass']}'")
