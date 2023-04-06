import time
import urllib3
import json

from inc.helper import Helper
from cfg.config_parser import VHI_CREDS, configs, ADMIN_AUTH
from inc.logger import logs
from inc.ssh_connector import SSH
from inc.utils import generate_random_password, exit_status_code_handler
from inc.vinfra_wrapper import (
    VinfraFlavor,
    VinfraUser,
    VinfraNode,
    VinfraImage,
    VinfraProject,
    VinfraStoragePolicies,
    VinfraQuotas,
)


# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Vhi:
    # VHI ROLES:
    VHI_ADMIN = "domain_admin"
    VHI_PROJECT_MEMBER = "project_admin"

    # API URL
    _URL = f"{VHI_CREDS['url']}{VHI_CREDS['api_path']}"
    _VHI_DOMAIN_API = f"{_URL}/domains/{VHI_CREDS['domain_id']}"
    _SPACES = Helper.SPACES.value
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'
    PATCH = 'PATCH'

    def __init__(self):
        self._cookie = ""
        self.project_id = ""
        self.project_name = ""
        self.user_id = ""
        self.flavor_name = ""
        self.vinfra_domain = VHI_CREDS['vinfra_domain']
        self.domain_id = VHI_CREDS['domain_id']
        self._storage_id = ""
        self._storage_name = ""
        self._vhi_ssh = SSH(**{'host': VHI_CREDS['cp_ip'], 'port': VHI_CREDS['cloud_ssh_port']})

    @staticmethod
    def _vhi_flavor_payload(vm_data: dict):
        return json.dumps({"name": vm_data['name'],
                           "vcpus": vm_data['vcpus'],
                           "ram": vm_data['ram'],
                           "disk": 0})

    def clean_up_cache(self):
        _cmd = 'rm -f ~/.vinfra/backend-api.svc.vstoragedomain/*'
        logs.info('Clean Up cache on VHI side in "~/.vinfra/backend-api.svc.vstoragedomain/*" path.', header=True)
        exit_status, output = self._vhi_ssh.execute(command=_cmd)
        if not exit_status_code_handler(exit_code=exit_status,
                                        message='Cache has not been cleaned up.'):
            return False

        return True

    def check_default_project(self):
        """
        We had situation when we do not have "Default" project for migrations.
        This function is checking whether we have such project otherwise create new one and set values into
         `config.cfg` file
        :return:
        """
        _default_name = 'Default_Project'
        _create_project = (f"{ADMIN_AUTH} domain project create '{_default_name}' "
                           f"--domain='{self.vinfra_domain}' --enable "
                           f"--description='Default project for migrations.' -f json")
        _projects_cmd = f"{ADMIN_AUTH} domain project list --domain='{self.vinfra_domain}' -f json"
        exit_status, output_proj = self._vhi_ssh.execute(_projects_cmd)
        if not exit_status_code_handler(exit_code=exit_status,
                                        message='Listing project failed. Please take a look manually.'):
            return False

        if _default_name not in [proj['name'] for proj in json.loads(output_proj)]:
            # Create new `project` and set name into config file
            logs.warn(f'*** "{_default_name}" project was not found on VHI side. Creating new one.\n')
            exit_status, output = self._vhi_ssh.execute(_create_project)
            project = json.loads(output)
            self.project_id = project['id']
            self.project_name = project['name']
            configs.set_new_value(configs.VHI, "vinfra_project", json.loads(output)['name'])
            return True

        else:
            self.project_name = _default_name
            logs.info(f'*** "{_default_name}" project was found on VHI side. Move all stuff there.')
            return True

    def update_user_password(self, user_login: str):
        _pwd = generate_random_password()
        _change_pwd = (f"echo -e '{_pwd}' | {ADMIN_AUTH} domain user set '{user_login}'"
                       f" --password --domain {self.vinfra_domain}")
        self._vhi_ssh.execute(_change_pwd)
        return _pwd

    def flavor_handler(self, onapp_flavor: dict):
        """
        Method purpose is to verify flavor on VHI side and check whether it exists or not and create new one
        :param onapp_flavor:
        :return:
        """
        _flavor_name = onapp_flavor['name']
        _payload = self._vhi_flavor_payload(vm_data=onapp_flavor)
        _vinfra = VinfraFlavor(service_user=True)
        exit_status, output = _vinfra.flavor_list()
        if not exit_status_code_handler(exit_code=exit_status,
                                        message=f'Impossible to get Flavor list. Output:\n\t{output}'):
            return False

        _vhi_flavors = [_flavor['name'] for _flavor in json.loads(output)]
        logs.debug(f'VHI existing flavors: {_vhi_flavors}')
        if _flavor_name in _vhi_flavors:
            self.flavor_name = _flavor_name
            return True

        exit_status, output = _vinfra.create(flavor_name=_flavor_name,
                                             vcpus=onapp_flavor['vcpus'],
                                             ram=onapp_flavor['ram'])
        if not exit_status_code_handler(exit_code=exit_status,
                                        message=f'Flavor has NOT been created. Output:\n\t{output}'):
            return False

        self.flavor_name = json.loads(output)['name']
        return True

    def _verify_user_exists(self, user_email: str, domain: str):
        """
        Verify whether user exists on VHI side or not
        :param user_email:
        :return:
        """
        v_user = VinfraUser()

        # Get List of users
        exit_status, output = v_user.user_list(domain=domain)
        _user_emails = [_user['email'] for _user in json.loads(output)]
        if user_email in _user_emails:
            return True

        return False

    def _create_domain_service_user(self):
        """
        Create Domain Service User for specified Domain:
            - echo -e "123456789@" | vinfra --vinfra-username='admin' --vinfra-password='4OnApp13777'
                 domain user create test123 --email "migration_helper@user.com" --domain-permissions domain_admin
                    --domain "MultiDomain"  --enable -f json
        Set Compute role to new user or to an existing one
            - vinfra domain user set test123 --assign-domain MultiDomain compute --domain=MultiDomain
        :return:
        """
        v_user = VinfraUser(cp_ip=True)
        _pwd = generate_random_password()
        _domain_service_user = {"email": f"{self.vinfra_domain}@user.com",
                                "name": f"dom_migration_user_{self.vinfra_domain.lower()}",
                                "enable": True,
                                "domain-permissions": 'domain_admin',
                                "domain": self.vinfra_domain}
        result = self._verify_user_exists(user_email=_domain_service_user['email'],
                                          domain=self.vinfra_domain)
        if result:
            if not VHI_CREDS['vinfra_domain_user'] or VHI_CREDS['vinfra_domain_user'] == "''":
                configs.set_new_value(section=configs.VHI,
                                      option="vinfra_domain_user",
                                      value=_domain_service_user['name'])
                domain_auth = configs.reset_domain_auth()
                import inc.vinfra_wrapper as wrapper
                wrapper.DOMAIN_AUTH = domain_auth

            v_image = VinfraImage(channel_timeout=5)
            exit_status, output = v_image.images()
            if not exit_status_code_handler(exit_code=exit_status,
                                            message=f'Domain Service User password is wrong. Output:\n\t{output}'):
                _new_pwd = self.update_user_password(user_login=_domain_service_user['name'])
                logs.warn(msg='Changed password to the new one for Domain Service User')
                configs.set_new_value(section=configs.VHI, option="vinfra_domain_pass", value=_new_pwd)
                domain_auth = configs.reset_domain_auth()
                import inc.vinfra_wrapper as wrapper
                wrapper.DOMAIN_AUTH = domain_auth
            return True

        exit_status, output = v_user.create(user_data=_domain_service_user, pwd=_pwd)
        if not exit_status_code_handler(exit_code=exit_status,
                                        message=f'Domain Service User has not been created. Output:\n\t{output}'):
            return False

        v_user.set(user_name=_domain_service_user['name'],
                   domain=self.vinfra_domain,
                   assign_domain=[self.vinfra_domain, 'compute'])
        configs.set_new_value(section=configs.VHI, option="vinfra_domain_user", value=_domain_service_user['name'])
        configs.set_new_value(section=configs.VHI, option="vinfra_domain_pass", value=_pwd)
        domain_auth = configs.reset_domain_auth()
        import inc.vinfra_wrapper as wrapper
        wrapper.DOMAIN_AUTH = domain_auth
        return True

    def create_service_user(self):
        """
        Creates new user and assign to him Service User role to be able
        to do any manipulations with compute resources within Domain
        If such user is created it will just take it creds from cfg/config.cfg file
        Manually command:
        `vinfra domain user set migration_user@onapp.test.com --assign-domain Default compute --domain=Default`
        :return:
        """
        v_user = VinfraUser(cp_ip=True)
        _pwd = generate_random_password()
        _service_user_payload = {"email": "migration_helper@user.com",
                                 "system-permissions": 'compute',
                                 "name": "migration_user",
                                 "enable": True,
                                 "assign-domain": ('Default', 'compute'),
                                 "domain": 'Default'}

        # Get List of users
        if VHI_CREDS['vinfra_user'] != _service_user_payload['name']:
            configs.set_new_value(section=configs.VHI, option="vinfra_user", value=_service_user_payload['name'])
            vinfra_auth = configs.reset_auth()
            import inc.vinfra_wrapper as wrapper
            wrapper.VINFRA_AUTH = vinfra_auth

        if self.vinfra_domain != 'Default':
            domain_user = self._create_domain_service_user()
            if not domain_user:
                return False

        result = self._verify_user_exists(user_email=_service_user_payload['email'],
                                          domain='Default')
        if result:
            _msg = (f'``Service User`` with Email: {_service_user_payload["email"]} exists on VHI side.'
                    f' Checking ``Service User`` credentials. . .')
            logs.info(msg=_msg, header=True)
            vinfra_node = VinfraNode(channel_timeout=5)
            exit_status, output = vinfra_node.list_node()
            if not exit_status_code_handler(exit_code=exit_status,
                                            message=f'Service User creds are not valid. Output:\n\t{output}'):
                logs.debug('Updating credentials for SERVICE USER and save them into `cfg/config.cfg`')

                # Generating new pwd for Service User and save it into config file, after check credentials again
                self.vinfra_domain = 'Default'
                new_pwd = self.update_user_password(user_login=_service_user_payload['name'])
                self.vinfra_domain = VHI_CREDS['vinfra_domain']
                configs.set_new_value(section=configs.VHI, option="vinfra_pass", value=new_pwd)
                vinfra_auth = configs.reset_auth()
                import inc.vinfra_wrapper as wrapper
                wrapper.VINFRA_AUTH = vinfra_auth
                v_node = VinfraNode(channel_timeout=5)
                exit_status, output = v_node.list_node()
                if not exit_status_code_handler(exit_code=exit_status,
                                                message=f'Updating Service User creds failed. Output:\n\t{output}'):
                    return False

                try:
                    assert type(json.loads(output)) == list
                except AssertionError:
                    logs.error(f'Service User password has NOT been changed. Output from getting node list:\n{output}')
                    return False
                logs.info(msg=f'SERVICE USER password has been updated,'
                              f' credentials saved into `cfg/config.cfg`')
                return True

            logs.info(msg=f'SERVICE USER credentials are valid and stored in `cfg/config.cfg`')
            return True

        exit_status, output = v_user.create(user_data=_service_user_payload, pwd=_pwd)
        if not exit_status_code_handler(exit_code=exit_status,
                                        message=f'Service User has not been created. Output:\n\t{output}'):
            return False

        user_response = json.loads(output)
        try:
            assert _service_user_payload['system-permissions'] in user_response['system_permissions']
            assert _service_user_payload['email'] == user_response['email']
            assert _service_user_payload['name'] == user_response['name']
        except AssertionError:
            logs.error(f'Service User has NOT been created. Output: {user_response}')
            return False

        # Save password to cfg/config.cfg file and after that verify ability to get list of nodes
        configs.set_new_value(section=configs.VHI, option="vinfra_pass", value=_pwd)
        vinfra_auth = configs.reset_auth()
        import inc.vinfra_wrapper as wrapper
        wrapper.VINFRA_AUTH = vinfra_auth
        time.sleep(1)
        v_node = VinfraNode(channel_timeout=5)
        exit_status, output = v_node.list_node()
        try:
            assert exit_status_code_handler(exit_code=exit_status)
            assert type(json.loads(output)) == list
        except AssertionError:
            logs.error(f'Service User password has NOT been changed. Output from getting node list:\n{output}')
            return False

        logs.info(msg=f'Service user has been created, credentials saved into `cfg/config.cfg`')
        return True

    def create_project(self, user_data: dict):
        """
        Create project on VHI side
        :param user_data: {
            "user_email": "roman.holovko@virtuozzo.com",
            "id": 4,
            "first_name": "Roman",
            "last_name": "Holovko",
            "password": "pwd",
                "user_login": "roman_holovko@virtuozzo_com",
            "project_name": "project_roman.holovko@virtuozzo.com",
            "quotas": {
              "cores": -1,
              "RAM": -1,
              "storage": -1
            },
            "virtual_machines": [. . .]
        :return:
        """
        project_name = user_data['project_name']
        quotas = user_data['quotas']
        _v_project = VinfraProject()
        exit_status, projects = _v_project.projects(**{'domain': self.vinfra_domain})
        _projects = [_proj['name'] for _proj in json.loads(projects)]
        if project_name in _projects:
            logs.warn(msg=f'Project with name `{project_name}` exists on VHI side!')
            self.project_name = project_name
            return True

        # Create new project
        logs.info(msg=f"{Helper.SPACES.value} -- Creating new project [{project_name}] on VHI side.", header=True)
        exit_status, output = _v_project.create(
            project_name=project_name,
            domain=self.vinfra_domain,
            description=f"OnApp User {user_data['first_name']} {user_data['last_name']}"
        )
        if not exit_status_code_handler(exit_code=exit_status,
                                        message=f'New Project was NOT created. Output:\n\t{output}'):
            return False

        create_project = json.loads(output)
        self.project_id = create_project['id']
        self.project_name = create_project['name']
        configs.set_new_value(configs.VHI, "vinfra_project", self.project_name)

        # Storage Policies
        v_storage = VinfraStoragePolicies()
        exit_status, storage_output = v_storage.storage_policy_list()
        storage_policy_name = json.loads(storage_output)[0]['name']
        new_quotas = {}
        for quota_name, quota_value in quotas.items():
            if quota_value == -1:
                continue

            if quota_name == 'storage':
                new_quotas['storage-policy'] = {'name': storage_policy_name,
                                                'size': quota_value}
                continue

            new_quotas[quota_name] = quota_value

        # Set Quotas
        if new_quotas:
            v_quotas = VinfraQuotas()
            logs.info(msg=f"Setting Up quotas for project [{project_name}] on VHI side.", header=True)
            exit_status, output = v_quotas.update_quotas(project_id=self.project_id, **new_quotas)
            exit_status_code_handler(exit_code=exit_status,
                                     message=f'Quotas has NOT been set for Project {self.project_name}.'
                                             f' Output:\n\t{output}\n\tPlease set quotas MANUALLY.')

        return True

    def create_user(self, user_data: dict):
        """
        Create User on VHI side
        :param user_data: {
            "user_email": "roman.holovko@virtuozzo.com",
            "id": 4,
            "first_name": "Roman",
            "last_name": "Holovko",
            "password": "pwd",
                "user_login": "roman_holovko@virtuozzo_com",
            "project_name": "project_roman.holovko@virtuozzo.com",
            "quotas": {
              "cores": -1,
              "RAM": -1,
              "storage": -1
            },
            "virtual_machines": [. . .]
        :return:
        """
        v_user = VinfraUser()
        self.project_name = user_data["project_name"]
        result = self._verify_user_exists(user_email=user_data['user_email'], domain=self.vinfra_domain)
        if result:
            logs.warn(msg=f'User with email [{user_data["user_email"]}] exists on VHI side.')
            _new_pwd = self.update_user_password(user_login=user_data['user_login'])
            return True, _new_pwd

        # Create new user
        _user_role = ''
        _user = {"email": user_data['user_email'],
                 "name": user_data['user_login'],
                 "enable": True,
                 "domain": self.vinfra_domain}
        for role in user_data['roles']:
            if role['role']['identifier'] == "admin":
                _user_role = self.VHI_ADMIN
                break

            _user_role = self.VHI_PROJECT_MEMBER
        if _user_role == self.VHI_ADMIN:
            _user.update({"domain-permissions": _user_role})
        else:
            _user.update({"assign": (self.project_name, _user_role)})

        logs.info(msg=f"{Helper.SPACES.value} -- Creating new user [{_user['name']}] on VHI side.", header=True)
        _pwd = generate_random_password()
        exit_status, output = v_user.create(user_data=_user, pwd=_pwd)
        if not exit_status_code_handler(exit_code=exit_status,
                                        message=f'New User was NOT created. Output:\n\t{output}'):
            return False, ''

        new_user = json.loads(output)
        self.user_id = new_user['id']
        return True, _pwd
