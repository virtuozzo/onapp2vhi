from configparser import ConfigParser
from typing import Dict


class AttributeDict(dict):
    def __getattr__(self, key):
        if key not in self:
            raise AttributeError(key)
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


class OnApp2VHIConfig:
    """
    Parsing config.ini file to get credentials to different resources
    """

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config=None, config_path=None):
        if isinstance(config, ConfigParser):
            self._config = config
            self._config_path = config_path

        if not hasattr(self, "_config"):
            raise RuntimeError("Config missing. run load_config() first")

    @classmethod
    def load_config(cls, config_path):
        with open(config_path, "r", encoding="utf8") as conf:
            config = ConfigParser(interpolation=None)
            config.read_file(conf)

        return cls(config, config_path)

    def get_config(self, cp_type=None):
        """
        load config by config_type
        """
        config = {}
        if cp_type:
            for section in self._config.sections():
                config[section] = {
                    key: self._config[section][key]
                    for key in self._config[section]
                }
            config = config[cp_type]
            return AttributeDict(**config)
        return {"error: Config type is not set"}

    @property
    def onapp_conf(self) -> Dict:
        """
        :return: OnApp CP properties
        """
        return self.get_config("onapp")

    @property
    def vhi_conf(self) -> Dict:
        """
        :return: VHI Cloud properties
        """
        return self.get_config("vhi")

    @property
    def ssh_key(self) -> str:
        return self._config.get(
            "key",
            "ssh_key",
        )

    def update(self, section: str, option: str, value: str):
        """
        Update config file
        """
        self._config.set(section, option, value)
        with open(self._config_path, "w+") as conf:
            self._config.write(conf)

    @property
    def VINFRA_AUTH(self):
        return (
            f"vinfra --vinfra-username='{self.vhi_conf['vinfra_user']}'"
            f" --vinfra-password='{self.vhi_conf['vinfra_pass']}'"
        )

    @property
    def ADMIN_AUTH(self):
        return (
            f"vinfra --vinfra-username='{self.vhi_conf['login']}'"
            f" --vinfra-password='{self.vhi_conf['admin_ui_pwd']}'"
        )

    @property
    def DOMAIN_AUTH(self):
        return (
            f"vinfra --vinfra-username='{self.vhi_conf['vinfra_domain_user']}'"
            f" --vinfra-password='{self.vhi_conf['vinfra_domain_pass']}'"
        )
