import time
import sys
import urllib3
import json

from onapp2vhi.inc.helper import Helper
from onapp2vhi.utilities.logs.logger import OnAppVHILogger
from onapp2vhi.inc.ssh_connector import SSH
from onapp2vhi.inc.utils import generate_random_password, exit_status_code_handler
from onapp2vhi.inc.vinfra_wrapper import (
    VinfraFlavor,
    VinfraUser,
    VinfraNode,
    VinfraImage,
    VinfraProject,
    VinfraStoragePolicies,
    VinfraQuotas,
    VinfraPlacement,
    VinfraError,
)
from onapp2vhi.utilities.config import OnApp2VHIConfig
from onapp2vhi.utilities.regex import JSON_REGEX

logs = OnAppVHILogger()

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Vhi:
    # VHI ROLES:
    VHI_ADMIN = "domain_admin"
    VHI_PROJECT_MEMBER = "project_admin"

    # API URL
    _SPACES = Helper.SPACES.value
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'
    PATCH = 'PATCH'

    def __init__(self, cfg: OnApp2VHIConfig):
        self.cfg = cfg
        self._cookie = ""
        self.project_id = ""
        self.project_name = ""
        self.user_id = ""
        self.flavor_name = ""
        self.vinfra_domain = self.cfg.vhi_conf['vinfra_domain']
        self.domain_id = self.cfg.vhi_conf['domain_id']
        self._storage_id = ""
        self._storage_name = ""
        self._vhi_ssh = SSH(**{'host': self.cfg.vhi_conf['cp_ip'],
                               'port': int(self.cfg.vhi_conf['cloud_ssh_port']),
                               'ssh_key': self.cfg.ssh_key})

    @staticmethod
    def _vhi_flavor_payload(vm_data: dict):
        return json.dumps({"name": vm_data['name'],
                           "vcpus": vm_data['vcpus'],
                           "ram": vm_data['ram'],
                           "disk": 0})

    def set_project_value(self, project_name: str):
        self.cfg.update(section="vhi", option="vinfra_project", value=project_name)

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
        _create_project = (f"{self.cfg.ADMIN_AUTH} domain project create '{_default_name}' "
                           f"--domain='{self.vinfra_domain}' --enable "
                           f"--description='Default project for migrations.' -f json")
        _projects_cmd = f"{self.cfg.ADMIN_AUTH} domain project list --domain='{self.vinfra_domain}' -f json"
        exit_status, output_proj = self._vhi_ssh.execute(_projects_cmd)
        if not exit_status_code_handler(exit_code=exit_status,
                                        message='Listing project failed. Please take a look manually.'):
            return False

        if self.domain_id != json.loads(output_proj)[0]['domain_id']:
            logs.warn(f'Domain ID {self.domain_id} in cfg is not the same as vinfra domain {self.vinfra_domain} id. Updating domain_id in cfg')
            self.cfg.update("vhi", "domain_id", json.loads(output_proj)[0]['domain_id'])

        if _default_name not in [proj['name'] for proj in json.loads(output_proj)]:
            # Create new `project` and set name into config file
            logs.warn(f'*** "{_default_name}" project was not found on VHI side. Creating new one.\n')
            exit_status, output = self._vhi_ssh.execute(_create_project)
            project = json.loads(output)
            self.project_id = project['id']
            self.project_name = project['name']
            self.cfg.update("vhi", "vinfra_project", json.loads(output)['name'])
            return True

        else:
            self.project_name = _default_name
            logs.info(f'*** "{_default_name}" project was found on VHI side. Move all stuff there.')
            return True

    def update_user_password(self, user_login: str):
        _pwd = generate_random_password()
        _change_pwd = (f"echo -e '{_pwd}' | {self.cfg.ADMIN_AUTH} domain user set '{user_login}'"
                       f" --password --domain {self.vinfra_domain}")
        self._vhi_ssh.execute(_change_pwd)
        return _pwd

    def flavor_handler(self, onapp_flavor: dict, placement=''):
        """
        Method purpose is to verify flavor on VHI side and check whether it exists or not and create new one
        :param onapp_flavor: flavor object
        :param placement: placement name or ID
        :return:
        """

        # check placement
        vinfra_placement = VinfraPlacement(self.cfg)
        if placement:
            try:
                output = vinfra_placement.list()
                placements = json.loads(output)
            except VinfraError as e:
                exit_status_code_handler(exit_code=e.exit_code,
                                         message=f'Listing placements failed.\n\t{e}')
                return False

            if not placements:
                exit_status_code_handler(1, 'no placements found')
                return False

            placement_id = None
            for x in placements:
                if x['name'] == placement:
                    placement_id = x['id']
                    break
            if not placement_id:
                exit_status_code_handler(1, message=f'{placement} not found')
                return False

            # check project quota
            proj_name = self.cfg.vhi_conf['vinfra_project']
            domain = self.cfg.vhi_conf['vinfra_domain']

            vinfra_project = VinfraProject(self.cfg)
            try:
                output = vinfra_project.show(proj_name, domain)
                proj_id = json.loads(output)['id']

                vinfra_quotas = VinfraQuotas(self.cfg, service_user=False, access_domain=True)
                try:
                    output = vinfra_quotas.show_quotas(proj_id)

                    m = JSON_REGEX.match(output)
                    if not m:
                        exit_status_code_handler(
                            1, message=f'unable to parse quota data. data = {output}')
                        return False

                    quotas = json.loads(m.group(0))
                    if quotas['placement'][placement_id]['limit'] == 0:
                        exit_status_code_handler(
                            1,
                            message=f'Project {proj_name} is not configured for placement = '
                                    f'{placement}')
                        return False

                except VinfraError as e:
                    exit_status_code_handler(exit_code=e.exit_code,
                                             message=f'Unable to check project quotas {proj_id}.\n\t{e}')
                    return False
            except VinfraError as e:
                exit_status_code_handler(exit_code=e.exit_code,
                                         message=f'Unable to check project {proj_name}.\n\t{e}')
                return False

        # check flavor
        _flavor_name = onapp_flavor['name']
        self._vhi_flavor_payload(vm_data=onapp_flavor)
        _vinfra = VinfraFlavor(self.cfg, service_user=True)
        try:
            output = _vinfra.flavor_list()
        except VinfraError as e:
            exit_status_code_handler(exit_code=e.exit_code,
                                     message=f'Impossible to get Flavor list.\n\t{e}')
            return False

        _vhi_flavors = [_flavor['name'] for _flavor in json.loads(output)]
        logs.debug(f'VHI existing flavors: {_vhi_flavors}')
        if _flavor_name in _vhi_flavors:
            self.flavor_name = _flavor_name
            if placement:
                logs.info(msg=f"{Helper.SPACES.value} -- Assigning placement to the flavor on VHI side.", header=True)
                try:
                    output = vinfra_placement.assign_placement_to_flavor(flavor=self.flavor_name,
                                                                         placement=placement)
                except VinfraError as e:
                    # log initial error and continue by creating flavor and assign
                    exit_status_code_handler(exit_code=e.exit_code,
                                             message=f'Placement Assignment result.\n\t{e}')
            return True

        try:
            output = _vinfra.create(flavor_name=_flavor_name,
                                    vcpus=onapp_flavor['vcpus'],
                                    ram=onapp_flavor['ram'])
        except VinfraError as e:
            exit_status_code_handler(exit_code=e.exit_code,
                                     message=f'Flavor has NOT been created.\n\t{e}')
            return False

        self.flavor_name = json.loads(output)['name']
        if placement:
            logs.info(msg=f"{Helper.SPACES.value} -- Assigning placement to the flavor on VHI side.", header=True)
            try:
                output = vinfra_placement.assign_placement_to_flavor(flavor=self.flavor_name,
                                                                     placement=placement)
            except VinfraError as e:
                exit_status_code_handler(exit_code=e.exit_code,
                                         message=f'Placement Assignment result.\n\t{e}')
                return False
        return True

    def _verify_user_exists(self, user_email: str, domain: str):
        """
        Verify whether user exists on VHI side or not
        :param user_email:
        :return:
        """
        v_user = VinfraUser(self.cfg)

        # Get List of users
        output = v_user.user_list(domain=domain)
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
        v_user = VinfraUser(self.cfg)
        _pwd = generate_random_password()
        _domain_service_user = {"email": f"{self.vinfra_domain}@user.com",
                                "name": f"dom_migration_user_{self.vinfra_domain.lower()}",
                                "enable": True,
                                "domain-permissions": 'domain_admin',
                                "domain": self.vinfra_domain}
        result = self._verify_user_exists(user_email=_domain_service_user['email'],
                                          domain=self.vinfra_domain)
        if result:
            if not self.cfg.vhi_conf['vinfra_domain_user'] or self.cfg.vhi_conf['vinfra_domain_user'] == "''" or\
                    self.cfg.vhi_conf['vinfra_domain_user'] != _domain_service_user['name']:
                self.cfg.update(section="vhi",
                                option="vinfra_domain_user",
                                value=_domain_service_user['name'])

            v_image = VinfraImage(self.cfg, channel_timeout=5)
            try:
                v_image.images()
            except VinfraError as e:
                exit_status_code_handler(exit_code=e.exit_code,
                                         message=f'Domain Service User password is wrong.\n\t{e}')
                _new_pwd = self.update_user_password(user_login=_domain_service_user['name'])
                logs.warn(msg='Changed password to the new one for Domain Service User')
                self.cfg.update(section="vhi", option="vinfra_domain_pass", value=_new_pwd)
            return True

        try:
            v_user.create(user_data=_domain_service_user, pwd=_pwd)
        except VinfraError as e:
            exit_status_code_handler(exit_code=e.exit_code,
                                     message=f'Domain Service User has not been created.\n\t{e}')
            return False

        v_user.set(user_name=_domain_service_user['name'],
                   domain=self.vinfra_domain,
                   assign_domain=[self.vinfra_domain, 'compute'])
        self.cfg.update(section="vhi", option="vinfra_domain_user", value=_domain_service_user['name'])
        self.cfg.update(section="vhi", option="vinfra_domain_pass", value=_pwd)
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
        v_user = VinfraUser(self.cfg)
        _pwd = generate_random_password()
        _service_user_payload = {"email": "migration_helper@user.com",
                                 "system-permissions": 'compute',
                                 "name": "migration_user",
                                 "enable": True,
                                 "assign-domain": ('Default', 'compute'),
                                 "domain": 'Default'}

        # Get List of users
        if self.cfg.vhi_conf['vinfra_user'] != _service_user_payload['name']:
            self.cfg.update(section="vhi", option="vinfra_user", value=_service_user_payload['name'])

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
            vinfra_node = VinfraNode(self.cfg, channel_timeout=5)
            try:
                output = vinfra_node.list_node()
            except VinfraError as e:
                exit_status_code_handler(exit_code=e.exit_code,
                                         message=f'Service User creds are not valid.\n\t{e}')
                logs.debug('Updating credentials for SERVICE USER and save them into `cfg/config.cfg`')

                # Generating new pwd for Service User and save it into config file, after check credentials again
                self.vinfra_domain = 'Default'
                new_pwd = self.update_user_password(user_login=_service_user_payload['name'])
                self.vinfra_domain = self.cfg.vhi_conf['vinfra_domain']
                self.cfg.update(section="vhi", option="vinfra_pass", value=new_pwd)
                v_node = VinfraNode(self.cfg, channel_timeout=5)
                try:
                    output = v_node.list_node()
                except VinfraError as e:
                    exit_status_code_handler(exit_code=e.exit_code,
                                             message=f'Updating Service User creds failed.\n\t{e}')
                    return False

                try:
                    assert type(json.loads(output)) == list
                except AssertionError:
                    logs.error(f'Service User password has NOT been changed. Output from getting node list:\n{output}')
                    return False
                logs.info(msg='SERVICE USER password has been updated,'
                              ' credentials saved into `cfg/config.cfg`')
                return True

            logs.info(msg='SERVICE USER credentials are valid and stored in `cfg/config.cfg`')
            return True

        try:
            output = v_user.create(user_data=_service_user_payload, pwd=_pwd)
        except VinfraError as e:
            exit_status_code_handler(exit_code=e.exit_code,
                                     message=f'Service User has not been created. {e}\n\t')
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
        self.cfg.update(section="vhi", option="vinfra_pass", value=_pwd)
        time.sleep(1)
        v_node = VinfraNode(self.cfg, channel_timeout=5)
        try:
            output = v_node.list_node()
            assert type(json.loads(output)) == list
        except VinfraError as e:
            logs.error('Service User password has NOT been changed. '
                       f'Output from getting node list:\n\t{e}')
            return False
        except AssertionError as e:
            logs.error('Service User password has NOT been changed. '
                       f'Output from getting node list:\n\t{e}')
            return False

        logs.info(msg='Service user has been created, credentials saved into `cfg/config.cfg`')
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
        _v_project = VinfraProject(self.cfg)
        projects = _v_project.projects(**{'domain': self.vinfra_domain})
        _projects = [_proj['name'] for _proj in json.loads(projects)]
        if project_name in _projects:
            logs.warn(msg=f'Project with name `{project_name}` exists on VHI side!')
            self.project_name = project_name
            return True

        # Create new project
        logs.info(msg=f"{Helper.SPACES.value} -- Creating new project [{project_name}] on VHI side.", header=True)
        try:
            output = _v_project.create(
                project_name=project_name,
                domain=self.vinfra_domain,
                description=f"OnApp User {user_data['first_name']} {user_data['last_name']}"
            )
        except VinfraError as e:
            exit_status_code_handler(exit_code=e.exit_code,
                                     message=f'New Project was NOT created.\n\t{e}')
            return False

        create_project = json.loads(output)
        self.project_id = create_project['id']
        self.project_name = create_project['name']
        self.cfg.update("vhi", "vinfra_project", self.project_name)

        # Storage Policies
        v_storage = VinfraStoragePolicies(self.cfg)
        storage_output = v_storage.storage_policy_list()
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
            v_quotas = VinfraQuotas(self.cfg)
            logs.info(msg=f"Setting Up quotas for project [{project_name}] on VHI side.", header=True)
            try:
                output = v_quotas.update_quotas(project_id=self.project_id, **new_quotas)
            except VinfraError as e:
                exit_status_code_handler(exit_code=e.exit_code,
                                         message=f'Quotas has NOT been set for Project '
                                                 f'{self.project_name}.\n\t{e}\n\tPlease set '
                                                 'quotas MANUALLY.')

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
        v_user = VinfraUser(self.cfg)
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
        try:
            output = v_user.create(user_data=_user, pwd=_pwd)
            new_user = json.loads(output)
            self.user_id = new_user['id']
            return True, _pwd
        except VinfraError as e:
            exit_status_code_handler(exit_code=e.exit_code,
                                     message=f'New User was NOT created.\n\t{e}')
            return False, ''


def get_vhi_hv_ip(cfg: OnApp2VHIConfig, vhi_vm_id: str, vhi_ssh):
    """
    Find HyperVisor IP address based on VM id
    :param vhi_vm_id: "59bbabef-b576-4339-b148-4adb6fcd4192"
    :param vhi_ssh: object with ssh access to VHI
    :return:
    """
    _migration_network_id = cfg.vhi_conf['migration_network_id']
    # Get Host Node hostname
    exit_status, server_output = vhi_ssh.execute(f"{cfg.ADMIN_AUTH} service compute server show {vhi_vm_id} -f json")
    _host = json.loads(server_output)['host']
    exit_status, node_output = vhi_ssh.execute(f"{cfg.ADMIN_AUTH} node list -f json")
    node_id = [node['id'] for node in json.loads(node_output) if node['host'] == _host][0]
    # Get ifaces at VHI side
    exit_status, iface_output = vhi_ssh.execute(f"{cfg.ADMIN_AUTH} node iface list --node {node_id} -f json")
    for iface in json.loads(iface_output):
        if iface['network'] == _migration_network_id:
            # When there is no IP address for HV returns False
            if not iface['ipv4']:
                msg = (f'There is no IP address for HV in this network: ["{_migration_network_id}"]'
                       f'\n\tvinfra node iface list --node {node_id}')
                logs.error(msg=msg)
                return False

            # Get HV IP address and return it
            ip_mask = iface['ipv4'][0]
            hv_ip = ip_mask.split('/')[0]
            logs.info(msg=f'*** Found VHI IP address [{hv_ip}] ***')
            return hv_ip

    msg = (f'Invalid migration network id: ["{_migration_network_id}"]'
           f'\n\tvinfra node iface list --node {node_id}')
    logs.error(msg=msg)
    sys.exit(1)
