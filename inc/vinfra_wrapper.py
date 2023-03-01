from typing import Optional, Tuple, Dict
from cfg.config_parser import VHI_CREDS, ADMIN_AUTH, VINFRA_AUTH
from inc.ssh_connector import SSH


class VinfraBase:

    def __init__(self, access: bool = False, service_user: bool = False):
        self.ssh = SSH(**{"host": VHI_CREDS['hv_ip']})
        self.vinfra_root = ADMIN_AUTH
        if service_user:
            self.vinfra_root = VINFRA_AUTH
        if access:
            self.vinfra_root += f" --vinfra-portal={VHI_CREDS['vinfra_portal']}" \
                                f" --vinfra-domain={VHI_CREDS['vinfra_domain']}" \
                                f" --vinfra-project={VHI_CREDS['vinfra_project']}"

    def execute(self, cmd: str) -> Tuple[int, str]:
        return self.ssh.execute(f'{cmd} -f json')


class VinfraServiceCompute(VinfraBase):

    def __init__(self, service_user: bool = False):
        super().__init__(service_user=service_user)
        self.vinfra_root += ' service compute'


class VinfraDomain(VinfraBase):

    def __init__(self):
        VinfraBase.__init__(self)
        self.vinfra_root += ' domain'


class VinfraServer(VinfraServiceCompute):

    def __init__(self, service_user: bool = False):
        super().__init__(service_user=service_user)
        self.vinfra_root += ' server'

    def create(self, server_name: str, **kwargs):
        """
        https://docs.virtuozzo.com/virtuozzo_hybrid_infrastructure_4_6_admins_cmd_guide/index.html#vinfra-service-compute-server-create.html
        --description <description>
        Virtual machine description
        --metadata <metadata>
        Virtual machine metadata
        --user-data <user-data>
        User data file
        --key-name <key-name>
        Key pair to inject
        --config-drive
        Use an ephemeral drive
        --count <count>
        If count is specified and greater than 1, the name argument is treated as a naming pattern.
        --ha-enabled {true,false}
        Enable or disable HA for the virtual machine.
        --placements <placements>
        Names or IDs of placements to add the virtual machine to.
        --network id|<id=id[,key=value,…]>
        Create a virtual machine with a specified network.
        Specify this option multiple times to create multiple networks.

        id: attach network interface to a specified network (ID or name)
        comma-separated key=value pairs with keys (optional):
        mac: MAC address for network interface
        fixed-ip: fixed IP address or None to automatically allocate an IP address.
        This option can be used multiple times.
        spoofing-protection-enable: enable spoofing protection for network interface
        spoofing-protection-disable: disable spoofing protection for network interface
        security-group: security group ID or name. This option can be used multiple times.
        no-security-group: do not use a security group
        --volume <source=source[,key=value,…]>
        Create a virtual machine with a specified volume. Specify this option multiple times to create multiple volumes.

        source: source type (volume, image, snapshot, or blank)
        comma-separated key=value pairs with keys (optional):
        id: resource ID or name for the specified source type (required for source types volume, image, and snapshot)
        size: block device size, in gigabytes (required for source types image and blank)
        boot-index: block device boot index (required for multiple volumes with source type volume)
        bus: block device controller type (scsi)
        type: block device type (disk or cdrom)
        rm: remove block device on virtual machine termination (yes or no)
        storage-policy: block device storage policy
        --flavor <flavor>
        Flavor ID or name
        <server-name>
        A new name for the virtual machine
        """
        cmd = self.vinfra_root + f' create {server_name}'
        if kwargs:
            for key, value in kwargs.items():
                cmd += f'--{key} {value} '
        return self.execute(cmd)

    def list(self):
        """
        https://docs.virtuozzo.com/virtuozzo_hybrid_infrastructure_4_6_admins_cmd_guide/index.html#vinfra-service-compute-server-list.html
        --long
        Enable access and listing of all fields of objects.
        --limit <num>
        The maximum number of virtual machines to list. To list all virtual machines, set the option to -1.
        --marker <server>
        List virtual machines after the marker.
        --name <name>
        List virtual machines with the specified name or use a filter. Supported filter operator: contains.
        The filter format is <operator>:<value1>[,<value2>,…].
        --id <id>
        Show a server with the specified ID or list virtual machines using a filter.
        Supported filter operator: in. The filter format is <operator>:<value1>[,<value2>,…].
        --project <project>
        List virtual machines that belong to the specified project ID. Can only be performed by system administrators.
        --status <status>
        List virtual machines with the specified status.
        --task-status <task-status>
        List virtual machines that have the specified task status.
        --host <hostname>
        List virtual machines located on a node with the specified hostname.
        --placement <placement>
        List virtual machines added to a placement with the specified ID or use a filter.
        Supported filter operator: any. The filter format is <operator>:<value1>[,<value2>,…].
        """
        cmd = self.vinfra_root + ' list'
        return self.execute(cmd)

    def show(self, server_name: str):
        """
        https://docs.virtuozzo.com/virtuozzo_hybrid_infrastructure_4_6_admins_cmd_guide/index.html#vinfra-service-compute-server-show.html
        <server>
        Virtual machine ID or name
        """
        cmd = self.vinfra_root + f' show {server_name}'
        return self.execute(cmd)


class VinfraServerInterface(VinfraServer):

    def __init__(self):
        VinfraServer.__init__(self)
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

    def list(self, server_name: str, **kwargs):
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

    def __init__(self):
        VinfraServiceCompute.__init__(self)
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

    def list(self, **kwargs: Dict):
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

    def __init__(self):
        VinfraServiceCompute.__init__(self)
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

    def list(self, sg_group: str = '', list_all: bool = False, **kwargs):
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

    def __init__(self):
        VinfraDomain.__init__(self)
        self.vinfra_root += ' project'

    def create(self, project_name: str, domain: str, description: Optional[str] = None, enable=True, **kwargs):
        """
        --description <description>
        Project description
        --enable
        Enable project
        --disable
        Disable project
        --domain <domain>
        Domain name or ID
        <name>
        Project name
        """
        cmd: str = self.vinfra_root + f' create {project_name} --domain {domain}'
        if description:
            cmd += f' --description {description}'
        if enable:
            cmd += f' --enable'
        else:
            cmd += f' --disable'
        if kwargs:
            for key, value in kwargs.items():
                cmd += f' --{key} {value} '
        return self.execute(cmd)

    def list(self, project_name: str, list_all: bool = False, **kwargs):
        """
        --long
        Enable access and listing of all fields of objects.
        --domain <domain>
        Domain name or ID
        --limit <num>
        The maximum number of projects to list. To list all projects, set the option to -1.
        --marker <project>
        List projects after the marker.
        --name <name>
        List projects with the specified name or use a filter.
        Supported filter operator: contains. The filter format is <operator>:<value1>[,<value2>,…].
        --id <id>
        Show a project with the specified ID or list projects using a filter.
        Supported filter operator: in. The filter format is <operator>:<value1>[,<value2>,…].
        --tags <tag>[,<tag>,…]
        List projects with the specified tags (comma-separated) or use a filter.
        Supported filter operators: any, not_any. The filter format is <operator>:<value1>[,<value2>,…].
        """
        cmd: str = ''
        if list_all:
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

    def __init__(self, service_user: bool = False):
        super().__init__(service_user=service_user)
        self.vinfra_root += ' flavor'

    def create(self, flavor_name: str, vcpus: int, ram: int):
        """
        Create new flavor based on input values
        :param (str) flavor_name: "flavor_4_128"
        :param (int) vcpus: 3
        :param (int) ram: 2048
        """
        cmd: str = f'{self.vinfra_root} create {flavor_name} --vcpus={vcpus} --ram={ram}'
        return self.execute(cmd)

    def list(self, long: bool = True):
        """
        --long
        Enable access and listing of all fields of objects.
        -f json
        to get output in json format
        """
        cmd: str = f'{self.vinfra_root} list'
        if long:
            cmd = f"{cmd} --long"
        return self.execute(cmd)
