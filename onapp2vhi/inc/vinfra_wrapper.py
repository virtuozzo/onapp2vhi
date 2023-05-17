from typing import Optional, Tuple, Dict

from onapp2vhi.inc.ssh_connector import SSH, CONNECT_TIMEOUT, CHANNEL_TIMEOUT
from onapp2vhi.utilities.config import OnApp2VHIConfig


class VinfraBase:

    def __init__(self,
                 cfg: OnApp2VHIConfig,
                 access_domain: bool = False,
                 service_user: bool = False,
                 domain_service_user: bool = False,
                 connect_timeout: int = CONNECT_TIMEOUT,
                 channel_timeout: int = CHANNEL_TIMEOUT,
                 cp_ip: bool = False):
        self.cp_ip = cp_ip
        _host = cfg.vhi_conf['hv_ip']
        if self.cp_ip:
            _host = cfg.vhi_conf['cp_ip']
        self.ssh = SSH(**{"host": _host,
                          "connect_timeout": connect_timeout,
                          "channel_timeout": channel_timeout,
                          "ssh_key": cfg.ssh_key})
        self.vinfra_root = cfg.ADMIN_AUTH
        if service_user:
            self.vinfra_root = cfg.VINFRA_AUTH
        if domain_service_user:
            self.vinfra_root = cfg.DOMAIN_AUTH
        if access_domain:
            self.vinfra_root += f" --vinfra-domain={cfg.vhi_conf['vinfra_domain']}"

    def execute(self, cmd: str, long: bool = False, json: bool = True) -> Tuple[int, str]:
        if long:
            cmd += ' --long'
        if json:
            cmd += ' -f json'
        return self.ssh.execute(cmd)


class VinfraServiceCompute(VinfraBase):

    def __init__(self,
                 cfg: OnApp2VHIConfig,
                 service_user: bool = False,
                 domain_service_user: bool = False,
                 connect_timeout: int = CONNECT_TIMEOUT,
                 access_domain: bool = False,
                 channel_timeout: int = CHANNEL_TIMEOUT):
        super().__init__(cfg,
                         service_user=service_user,
                         access_domain=access_domain,
                         domain_service_user=domain_service_user,
                         connect_timeout=connect_timeout,
                         channel_timeout=channel_timeout)
        self.vinfra_root += ' service compute'


class VinfraNode(VinfraServiceCompute):

    def __init__(self,
                 cfg: OnApp2VHIConfig,
                 service_user: bool = True,
                 connect_timeout: int = CONNECT_TIMEOUT,
                 channel_timeout: int = CHANNEL_TIMEOUT):
        super().__init__(cfg,
                         service_user=service_user,
                         connect_timeout=connect_timeout,
                         channel_timeout=channel_timeout)
        self.vinfra_root += ' node'

    def list_node(self):
        """
        Get list of all nodes
        :return:
        """
        cmd: str = f'{self.vinfra_root} list'
        return self.execute(cmd)


class VinfraImage(VinfraServiceCompute):

    def __init__(self,
                 cfg: OnApp2VHIConfig,
                 access_domain: bool = True,
                 domain_service_user: bool = True,
                 connect_timeout: int = CONNECT_TIMEOUT,
                 channel_timeout: int = CHANNEL_TIMEOUT):
        super().__init__(cfg,
                         access_domain=access_domain,
                         domain_service_user=domain_service_user,
                         connect_timeout=connect_timeout,
                         channel_timeout=channel_timeout)
        self.vinfra_root += ' image'

    def images(self):
        """
        Get list of all nodes
        :return:
        """
        cmd: str = f'{self.vinfra_root} list'
        return self.execute(cmd)


class VinfraDomain(VinfraBase):

    def __init__(self, cfg: OnApp2VHIConfig):
        VinfraBase.__init__(self, cfg)
        self.vinfra_root += ' domain'


class VinfraServer(VinfraServiceCompute):

    def __init__(self, cfg: OnApp2VHIConfig, service_user: bool = False):
        super().__init__(cfg, service_user=service_user)
        self.vinfra_root += ' server'

    def create(self, server_name: str, **kwargs):
        """
        https://docs.virtuozzo.com/virtuozzo_hybrid_infrastructure_4_6_admins_cmd_guide/index.html#vinfra-service-compute-server-create.html
        Create virtual machine
        """
        cmd = self.vinfra_root + f' create {server_name}'
        if kwargs:
            for key, value in kwargs.items():
                cmd += f'--{key} {value} '
        return self.execute(cmd)

    def list_server(self):
        """
        List all Virtual Machines
        https://docs.virtuozzo.com/virtuozzo_hybrid_infrastructure_4_6_admins_cmd_guide/index.html#vinfra-service-compute-server-list.html
        """
        cmd = self.vinfra_root + ' list'
        return self.execute(cmd, long=True)

    def show(self, server_name: str):
        """
        https://docs.virtuozzo.com/virtuozzo_hybrid_infrastructure_4_6_admins_cmd_guide/index.html#vinfra-service-compute-server-show.html
        <server>
        Virtual machine ID or name
        """
        cmd = self.vinfra_root + f' show {server_name}'
        return self.execute(cmd)


class VinfraServerInterface(VinfraServer):

    def __init__(self, cfg: OnApp2VHIConfig):
        VinfraServer.__init__(self, cfg)
        self.vinfra_root += ' iface'

    def set(self, iface: str, vm_name: str = None, spoofing: bool = False, **kwargs):
        """
        --fixed-ip <ip-address>
        IP address or None to automatically allocate an IP address. This option can be used multiple times.
        --spoofing-protection-enable
        Enable spoofing protection for the network interface
        --spoofing-protection-disable
        Disable spoofing protection for the network interface
        --security-group <security-group>
        Security group ID or name. This option can be used multiple times.
        --no-security-groups
        Do not set security groups
        --server <server>
        Virtual machine ID or name
        <interface>
        Network interface ID
        """
        cmd: str = self.vinfra_root + f' set {iface} '
        if vm_name:
            cmd += f' --server {vm_name}'
        if spoofing:
            cmd += f' --spoofing-protection-enable '
        else:
            cmd += f' --spoofing-protection-disable '
        if kwargs:
            for key, value in kwargs.items():
                cmd += f'--{key} {value} '
        return self.execute(cmd)

    def list_server(self, server_name: str, **kwargs):
        """
        --long
        Enable access and listing of all fields of objects.
        --server <server>
        Virtual machine ID or name
        """
        cmd: str = self.vinfra_root + f' list '
        if server_name:
            cmd += f" --server {server_name}"
        if kwargs:
            for key, value in kwargs.items():
                cmd += f'--{key} {value} '
        return self.execute(cmd)


class VinfraSecurityGroups(VinfraServiceCompute):

    def __init__(self, cfg: OnApp2VHIConfig):
        VinfraServiceCompute.__init__(self, cfg)
        self.vinfra_root += ' security-group'

    def create(self, name: str, description: Optional[str] = None):
        """
        https://docs.virtuozzo.com/virtuozzo_hybrid_infrastructure_4_6_admins_cmd_guide/index.html#vinfra-service-compute-security-group-create.html
        --description <description>
        Security group description
        <name>
        Security group name
        """
        cmd = self.vinfra_root + f' create {name}' \
            if description is None else self.vinfra_root + f' create {name} --description "{description}"'
        return self.execute(cmd)

    def list_security_group(self, **kwargs: Dict):
        """
        https://docs.virtuozzo.com/virtuozzo_hybrid_infrastructure_4_6_admins_cmd_guide/index.html#vinfra-service-compute-security-group-list.html
        --long
        Enable access and listing of all fields of objects.
        --limit <num>
        The maximum number of security groups to list. To list all security groups, set the option to -1.
        --marker <router>
        List security groups after the marker.
        --name <name>
        List security groups with the specified name or use a filter. Supported filter operator: contains.
        The filter format is <operator>:<value1>[,<value2>,…].
        --id <id>
        Show a security group with the specified ID or list security groups using a filter. Supported filter operator:
        in. The filter format is <operator>:<value1>[,<value2>,…].
        --project <project>
        List security groups that belong to the specified project ID. Can only be performed by system administrators.
        """
        cmd = self.vinfra_root + ' list '
        if kwargs:
            for key, value in kwargs.items():
                cmd += f'--{key} {value} '
        return self.execute(cmd)


class VinfraSGRules(VinfraServiceCompute):

    def __init__(self, cfg: OnApp2VHIConfig):
        VinfraServiceCompute.__init__(self, cfg)
        self.vinfra_root += ' security-group rule '

    def create(self, sg_name: str, **kwargs):
        """
        https://docs.virtuozzo.com/virtuozzo_hybrid_infrastructure_4_6_admins_cmd_guide/index.html#vinfra-service-compute-security-group-rule-create.html
        --remote-group <remote-group>
        Remote security group name or ID
        --remote-ip <ip-address>
        Remote IP address block in CIDR notation
        --ethertype <ethertype>
        Ether type of network traffic: IPv4 or IPv6
        --protocol <protocol>
        IP protocol: tcp, udp, icmp, vrrp and others
        --port-range-max <port-range-max>
        The maximum port number in the port range that satisfies the security group rule
        --port-range-min <port-range-min>
        The minimum port number in the port range that satisfies the security group rule
        --ingress
        Rule for incoming network traffic
        --egress
        Rule for outgoing network traffic
        <security-group>
        Security group name or ID to create the rule in
        """
        cmd = self.vinfra_root + f' create {sg_name} '
        for key, value in kwargs.items():
            cmd += f'--{key} {value} '
        # onapp supports only incoming traffic, so the default value will be ingress
        return self.execute(f"{cmd} --ingress")

    def list_sg_rules(self, sg_group: str = '', list_all: bool = False, **kwargs):
        """
        --long
        Enable access and listing of all fields of objects.
        --limit <num>
        The maximum number of security group rules to list. To list all security group rules, set the option to -1.
        --marker <router>
        List security group rules after the marker.
        --id <id>
        Show a security group rule with the specified ID or list security group rules using a filter.
        Supported filter operator: in. The filter format is <operator>:<value1>[,<value2>,…].
        <group>
        List security group rules in a particular security group specified by name or ID.
        """
        cmd: str = ''
        if list_all:
            cmd = self.vinfra_root + ' list '
        if sg_group:
            cmd = self.vinfra_root + f' list {sg_group}'
        for key, value in kwargs.items():
            cmd += f'--{key} {value} '
        return self.execute(cmd)


class VinfraProject(VinfraDomain):

    def __init__(self, cfg: OnApp2VHIConfig):
        VinfraDomain.__init__(self, cfg)
        self.vinfra_root += ' project'

    def create(self, project_name: str, domain: str, description: Optional[str] = None, enable=True):
        """

        """
        cmd: str = self.vinfra_root + f' create {project_name} --domain {domain}'
        if description:
            cmd += f' --description "{description}"'
        if enable:
            cmd += f' --enable'
        else:
            cmd += f' --disable'
        return self.execute(cmd)

    def projects(self, project_name: Optional[str] = None, **kwargs):
        """
        Get list of projects
        :param project_name: str "New Project"
        :param kwargs: {}
        """
        cmd = self.vinfra_root + ' list '
        if project_name:
            cmd = self.vinfra_root + f' list {project_name}'
        if kwargs:
            for key, value in kwargs.items():
                cmd += f'--{key} {value} '
        return self.execute(cmd)

    def show(self, project_name: str, domain: str):
        """
        --domain <domain>
        Domain name or ID
        <project>
        Project ID or name
        """
        cmd = self.vinfra_root + f' show --domain {domain} {project_name}'
        return self.execute(cmd)


class VinfraFlavor(VinfraServiceCompute):

    def __init__(self, cfg: OnApp2VHIConfig, service_user: bool = False):
        super().__init__(cfg, service_user=service_user)
        self.vinfra_root += ' flavor'

    def create(self, flavor_name: str, vcpus: int, ram: int):
        """
        Create new flavor based on input properties
        :param (str) flavor_name: "flavor_4_128"
        :param (int) vcpus: 3
        :param (int) ram: 2048
        """
        cmd: str = f'{self.vinfra_root} create {flavor_name} --vcpus={vcpus} --ram={ram}'
        return self.execute(cmd)

    def flavor_list(self):
        """
        --long
        Enable access and listing of all fields of objects.
        """
        cmd: str = f'{self.vinfra_root} list'
        return self.execute(cmd)


class VinfraUser(VinfraBase):

    def __init__(self, cfg: OnApp2VHIConfig, cp_ip: bool = True):
        super().__init__(cfg, cp_ip=cp_ip)
        self.vinfra_root += ' domain user'

    def user_list(self, domain: str):
        """
        :param domain: Default
        """
        cmd: str = f'{self.vinfra_root} list --domain={domain}'
        return self.execute(cmd)

    def create(self, user_data: dict, pwd: str):
        """
        Create new user based on input properties
        :param (str) user_data: {
            "email": "migration_helper@user.com",
            "system-permissions": 'compute',
            "domain-permissions": 'compute',
            "name": "migration_user",
            "description": "",
            "enable": True,
            "assign-domain": default 'compute',
            "domain_permissions": "domain_admin",
            "assigned_projects": "project_id" "role"
            "domain": vinfra_domain
        }
        :param pwd: str
        :return execute command:
            "echo -e "{password}" | vinfra domain user create {user_name}
                                    --domain default
                                     --email 'test@test.com'
                                     --assign-domain default 'compute'
                                      --system-permissions 'compute'
                                       --enable -f json"
        """
        _cmd_properties = ''
        for key, value in user_data.items():
            if type(value) == bool:
                continue

            if key in ['name', 'assign-domain', 'assign']:
                continue

            _cmd_properties += f'--{key} "{value}" '
        cmd: str = f'echo -e "{pwd}" | {self.vinfra_root} create {user_data["name"]} {_cmd_properties}'
        if 'assign-domain' in list(user_data.keys()):
            cmd += f'--assign-domain {user_data["assign-domain"][0]} {user_data["assign-domain"][1]}'
        if 'assign' in list(user_data.keys()):
            cmd += f'--assign {user_data["assign"][0]} {user_data["assign"][1]}'
        # Handle bool values
        for _bool in ['enable', 'disable']:
            if _bool in list(user_data.keys()):
                if user_data[_bool]:
                    cmd += f' --{_bool}'

        return self.execute(cmd)

    def show(self, user_name: str, domain: str):
        """
        Get user details
        :param user_name: user_123
        :param domain: Default
        :return:
        """
        cmd: str = f'{self.vinfra_root} show --domain={domain} {user_name}'
        return self.execute(cmd)

    def set(self, user_name: str, domain: str, assign_domain: list):
        """
        Set any user details
        :param user_name: 'user_123'
        :param domain: 'Default'
        :param assign_domain: ['MultiDomain', 'compute']
        :return:
        """
        cmd: str = f'{self.vinfra_root} set {user_name}'
        if assign_domain:
            cmd = f'{cmd} --assign-domain {assign_domain[0]} {assign_domain[1]}'
        cmd += f' --domain {domain}'
        return self.execute(cmd)


class VinfraQuotas(VinfraServiceCompute):

    def __init__(self,
                 cfg: OnApp2VHIConfig,
                 service_user: bool = True,
                 connect_timeout: int = CONNECT_TIMEOUT,
                 channel_timeout: int = CHANNEL_TIMEOUT):
        super().__init__(cfg,
                         service_user=service_user,
                         connect_timeout=connect_timeout,
                         channel_timeout=channel_timeout)
        self.vinfra_root += ' quotas'

    def update_quotas(self, project_id: str, **kwargs):
        """
        Get list of all nodes
        :param project_id: "8yse873huc39en0v"
        :param kwargs: {}
        :return:
        """
        _cmd_properties = ''
        cmd: str = f'{self.vinfra_root} update {project_id}'
        for key, value in kwargs.items():
            if key == "storage-policy":
                continue

            _cmd_properties += f'--{key} "{value}" '
        if "storage-policy" in list(kwargs.keys()):
            _cmd_properties += f'--storage-policy' \
                               f' {kwargs["storage-policy"]["name"]}:{kwargs["storage-policy"]["size"]}G'
        cmd = f"{cmd} {_cmd_properties}"
        return self.execute(cmd, json=False)


class VinfraStoragePolicies(VinfraServiceCompute):

    def __init__(self,
                 cfg: OnApp2VHIConfig,
                 service_user: bool = True,
                 connect_timeout: int = CONNECT_TIMEOUT,
                 channel_timeout: int = CHANNEL_TIMEOUT):
        super().__init__(cfg,
                         service_user=service_user,
                         connect_timeout=connect_timeout,
                         channel_timeout=channel_timeout)
        self.vinfra_root += ' storage-policy'

    def storage_policy_list(self):
        """
        Get list of all storage_policy
        :return:
        """
        cmd: str = f'{self.vinfra_root} list'
        return self.execute(cmd)


class VinfraPlacement(VinfraServiceCompute):

    def __init__(self,
                 cfg: OnApp2VHIConfig,
                 connect_timeout: int = CONNECT_TIMEOUT,
                 channel_timeout: int = CHANNEL_TIMEOUT):
        super().__init__(cfg,
                         connect_timeout=connect_timeout,
                         channel_timeout=channel_timeout)
        self.vinfra_root += ' placement assign'

    def assign_placement_to_flavor(self, flavor: str, placement: str):
        """
        Assign placement to the flavor
        # vinfra {ADMIN_AUTH} service compute placement assign --flavors flavor_2_512 test_placement1
        :return:
        """
        cmd: str = f'{self.vinfra_root} --flavors {flavor} {placement}'
        return self.execute(cmd, json=False)
