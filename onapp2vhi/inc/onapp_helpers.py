import copy
import json
import re
import xml.etree.ElementTree as KVMxml

from onapp2vhi.inc.rest_client import OnAppRequests
from onapp2vhi.inc.helper import Helper
from onapp2vhi.inc.ssh_connector import ssh_run, SSH
from onapp2vhi.utilities.logs.logger import OnAppVHILogger
from onapp2vhi.inc.utils import parse_matrix, exit_status_code_handler, generate_random_password
from onapp2vhi.inc.network_onapp import get_virtual_server_interfaces, get_virtual_server_ip_addresses
from onapp2vhi.inc.network_onapp import get_vm_network_info
from os.path import join

from collections import namedtuple
from typing import List, Dict
from onapp2vhi.inc.vinfra_wrapper import (
    VinfraSecurityGroups,
    VinfraSGRules,
    VinfraProject,
    VinfraServerInterface,
    VinfraServer,
)
from onapp2vhi.utilities.config import OnApp2VHIConfig

logs = OnAppVHILogger()

_spaces = Helper.SPACES.value


class Bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARN = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


FirewallRules = namedtuple('FirewallRules', 'id position nic_id address command port protocol '
                                            ' comment source_port destination_ip protocol_type')
NIC = namedtuple('NIC', 'id vm_id label nic_idn is_primary mac network_join '
                        'default_firewall_rule is_connected ip_addr')
ComputeZone = namedtuple('ComputeZone', 'name cpu ram')
DataStoreZone = namedtuple('DataStoreZone', 'name storage_policy')

##############################################


def _find_by(find: str, obj: dict):
    """
    Find some object in the list
    :param find: str - "user_name=AQA Roman Holovko"
    :param obj: {'1': 1}
    :return:
    """
    by_arg = find.split("=")[0]
    by_val = find.split("=")[1]
    if by_arg in ('ip_addresses', 'ip_address', 'ip'):
        if not obj['ip_addresses']:
            return False

        if obj['ip_addresses'][0]['ip_address']['address'] == by_val:
            return True

    if by_arg in ('roles', 'role'):
        if obj['roles'][0]['role']['label'] == by_val:
            return True

    try:
        if str(obj[by_arg]) != by_val:
            return False

    except KeyError:
        return False

    return True


def _create_obj_list(obj_list: list, obj_name: str, default_props: list, find=''):
    """
    Create List of specified object to display info in the table
    :param obj_list: [{'1': 1}, {'2': 1}, {'3': 1}]
    :param obj_name: "virtual_machine", "user"
    :param default_props: ['id', 'label', . . .]
    :param find: str - "user_name=AQA Roman Holovko"
    :return:
    """
    new_list = []
    for _one_obj in obj_list:
        _obj_dict = _one_obj[obj_name]
        _one_vm = []
        if find:
            if not _find_by(find, _obj_dict):
                continue

        for value in default_props:
            if value in ('ip_addresses', 'ip_address', 'ip'):
                if not _obj_dict['ip_addresses']:
                    _one_vm.append(str('NO_IP_ADDRESS'))
                    continue

                _one_vm.append(str(_obj_dict['ip_addresses'][0]['ip_address']['address']))
                continue

            if value in ('roles', 'role'):
                if not _obj_dict['roles']:
                    continue

                _one_vm.append(str(_obj_dict['roles'][0]['role']['label']))
                continue

            _one_vm.append(str(_obj_dict[value]))
        if len(_one_vm) != len(default_props):
            continue

        new_list.append(_one_vm)
    return new_list


def list_onapp_vms(cfg: OnApp2VHIConfig, props='', find=''):
    """
    Get all virtual machines from OnApp Control Panel and show them in the terminal
    :param props: --props=identifier,hostname,memory,cpus,user_id,template_label,total_disk_size
    :param find: --find="identifier=lidqtfwggohyzk"
    :return:
    """
    onapp_requests = OnAppRequests(cfg)

    default_props = ['id', 'label', 'ip_address', 'identifier', 'template_label', 'booted', 'user_id']
    if props:
        _additional_vals = props.split(",")
        default_props = default_props + [_val for _val in _additional_vals if _val not in default_props]
    _virtual_machines = onapp_requests.get('virtual_machines')
    if _virtual_machines:
        vm_list = _create_obj_list(obj_list=_virtual_machines,
                                   obj_name='virtual_machine',
                                   default_props=default_props,
                                   find=find)
        if not vm_list:
            logs.error("No Virtual Servers found.")
            return

        logs.info(f'{_spaces} -- LIST ONAPP VIRTUAL MACHINES --')
        vms = parse_matrix(default_props, vm_list)
        logs.info(f"\n{vms}")
    else:
        logs.error("No Virtual Servers found.")


def list_onapp_users(cfg: OnApp2VHIConfig, props='', find=''):
    """
    Get all users from OnApp Control Panel and show them in the terminal
    :param props: --props=identifier,hostname,memory,cpus,user_id,template_label,total_disk_size
    :param find: --find="identifier=lidqtfwggohyzk"
    :return:
    """
    default_props = ['first_name', 'last_name', 'login', 'email', 'roles', 'id']
    if props:
        _additional_vals = props.split(",")
        default_props = default_props + [_val for _val in _additional_vals if _val not in default_props]
    onapp_requests = OnAppRequests(cfg)
    _users = onapp_requests.get('users')
    if _users:
        user_list = _create_obj_list(obj_list=_users,
                                     obj_name='user',
                                     default_props=default_props,
                                     find=find)
        logs.info(f'{_spaces} -- LIST ONAPP USERS --')
        if not user_list:
            logs.error("No Users found.")
            return

        users = parse_matrix(default_props, user_list)
        logs.info(f"\n{users}")
    else:
        logs.error("No Users found.")


def get_onapp_vm_nics(cfg: OnApp2VHIConfig, vm_idn: str) -> List[Dict]:
    """
    Get OnApp NIC's info
    :param vm_idn:
    :return:
    """
    onapp_requests = OnAppRequests(cfg)
    nic_res = onapp_requests.get(f'virtual_machines/{vm_idn}/network_interfaces')
    _onapp_nics = [{'id': _ni['network_interface']['id'],
                    'mac': _ni['network_interface']['mac_address'],
                    'primary': _ni['network_interface']['primary']} for _ni in nic_res]
    ip_addresses = onapp_requests.get(f'virtual_machines/{vm_idn}/ip_addresses')
    for _vm_mac in _onapp_nics:
        _vm_mac.update({'ips': []})
        for line in ip_addresses:
            _ip_addr = line['ip_address_join']
            if _vm_mac['id'] != _ip_addr['network_interface_id']:
                continue

            _vm_mac['ips'].append(_ip_addr['ip_address']['address'])
    logs.info(f'OnApp VM "{vm_idn}" NICs:')
    [logs.info(f"{nic}") for nic in _onapp_nics]
    return _onapp_nics


def get_onapp_vm_disks(cfg: OnApp2VHIConfig, vm_idn: str, primary=False):
    """
    Get Virtual Machine disks and specify Data Stores
    :param vm_idn: str - "lidqtfwggohyzk"
    :param primary: bool - whether we need just primary disk
    :return:
    """
    api_ds = {}
    api_vm_disks = []
    onapp_requests = OnAppRequests(cfg)
    data_stores_response = onapp_requests.get("settings/data_stores")
    for d_store in data_stores_response:
        _ds = d_store['data_store']
        api_ds[_ds['id']] = {'id': _ds['identifier'], 'type': _ds['data_store_type']}

    logs.info(f"ONAPP DATASTORES:\n{api_ds}")
    disks_response = onapp_requests.get(f"virtual_machines/{vm_idn}/disks")
    if disks_response:
        for _disk in disks_response:
            disk = _disk['disk']
            ds = api_ds[disk['data_store_id']]
            if primary and disk['primary']:
                return f'/dev/{ds["id"]}/{disk["identifier"]}'

            api_vm_disks.append({'datastore_idn': ds['id'],
                                 'number': disk['disk_vm_number'],
                                 'is_swap': disk['is_swap'],
                                 'primary': disk['primary'],
                                 'path': f'/dev/{ds["id"]}/{disk["identifier"]}',
                                 'ds_id': disk['id'],
                                 'disk_idn': disk['identifier'],
                                 'size': disk['disk_size'],
                                 'datastore_type': ds['type']})
    logs.info(f'OnApp VM "{vm_idn}" DISKS:')
    [logs.info(f'{disk_data}') for disk_data in api_vm_disks]
    return api_vm_disks


def get_onapp_vm_flavor(cfg: OnApp2VHIConfig, vm_idn: str):
    """
    Get ram, cpu, data store
    :param vm_idn: "lidqtfwggohyzk"
    :return:
    """
    onapp_requests = OnAppRequests(cfg)
    response = onapp_requests.get(f'virtual_machines/{vm_idn}')
    vm_props = response['virtual_machine']
    return {'vcpus': vm_props['cpus'],
            'ram': vm_props['memory'],
            'name': f"flavor_{vm_props['cpus']}_{vm_props['memory']}"}


def _get_onapp_bucket_access_controls(cfg: OnApp2VHIConfig, bucket_id: str):
    """
        Get access controls from the users bucket
        :param bucket_id: "1", "1000"
        :return: json of access controls
    """
    logs.info(f"{_spaces}-- OnApp: Get User Bucket Access Controls --   ", separator=True)
    onapp_requests = OnAppRequests(cfg)
    return onapp_requests.get(f'billing/buckets/{bucket_id}/access_controls')


def get_user_ssh_keys(cfg: OnApp2VHIConfig, user_data: dict) -> List:
    """
    Get user ssh keys and return them
    :param user_data: {"id": 3, "first_name": "Test1", "last_name": "Test2", . . .}
    :return: [ssh_key1, ssh_key2]
    """
    logs.info(f"{_spaces}-- OnApp: Get User SSH keys --  ", separator=True)
    onapp_requests = OnAppRequests(cfg)
    response = onapp_requests.get(f"users/{user_data['id']}/ssh_keys")
    _ssh_keys = [ssh_key['ssh_key']['key'] for ssh_key in response]
    return _ssh_keys


def get_user_data(cfg: OnApp2VHIConfig, url: str, get_type, value_to_search=None, all_users=False):
    """
    Get users data from OnApp platform
    :param url: /users or /users/1
    :param get_type: ID or any value in user obj
    :param value_to_search: value based on what we will find user
    :param all_users: bool True or False
    :return:
    """
    logs.info(f"{_spaces}-- OnApp: Get User information --  ", separator=True)
    onapp_requests = OnAppRequests(cfg)
    response = onapp_requests.get(url)
    if not response:
        return False

    if get_type == 'ID':
        return [response]

    if all_users:
        return response

    for _user in response:
        if value_to_search in list(_user['user'].values()):
            return _user['user']


def _get_primary_vm_ip(cfg: OnApp2VHIConfig, vm: dict):
    vm_idn = vm['identifier']
    version = onapp_version(cfg)
    if version <= 6.0:
        virtual_server_nic = get_virtual_server_interfaces(cfg, virtual_server_id=vm_idn)
        primary_nic_id = [nic["network_interface"]["id"] for nic in virtual_server_nic
                          if nic['network_interface']['primary']][0]
        vs_ip_addresses = get_virtual_server_ip_addresses(cfg,
                                                          virtual_server_id=vm_idn,
                                                          network_interface_id=primary_nic_id)
        return vs_ip_addresses[0]['address']
    else:
        for ip_address in vm['ip_addresses']:
            ip = ip_address['ip_address']
            if not ip['primary']:
                continue
            return ip['address']


def _vhi_virtual_machine_list(cfg: OnApp2VHIConfig):
    _vs = VinfraServer(cfg, service_user=False)
    exit_code, server_list = _vs.list_server()
    server_list = json.loads(server_list)
    return [vm['name'] for vm in server_list if vm['domain_id'] == cfg.vhi_conf['domain_id']]


def get_all_virtual_machines(cfg: OnApp2VHIConfig, user_id: int = None):
    """
    Get list of all virtual machines and sort them by user ID
    :param user_id: 4 - get that user VM's
    :return: list of VMs
    """
    logs.info(f"{_spaces}-- OnApp: Get All Virtual Machines information --  ", separator=True)
    onapp_requests = OnAppRequests(cfg)
    if user_id:
        response = onapp_requests.get('virtual_machines', params=f'search_filter[user_id]={user_id}')
    else:
        response = onapp_requests.get('virtual_machines')

    if not response:
        return False

    existing_vms = _vhi_virtual_machine_list(cfg)
    from collections import defaultdict
    vms_dict = defaultdict(list)
    for _vm in response:
        vm = _vm['virtual_machine']
        _ip_addr = _get_primary_vm_ip(cfg, vm)

        if f"{vm['hostname']}.{vm['domain']}".lower() in existing_vms:
            msg = (f'Virtual Machine already exists on VHI side in `{cfg.vhi_conf["vinfra_domain"]}` domain\n\n\t\t'
                   f'VM Info [{vm["identifier"]} | {_ip_addr} | {vm["hostname"]} | {vm["label"]}]\n')
            logs.warn(msg=msg)
            continue

        vms_dict[vm['user_id']].append({'id': vm['identifier'],
                                        'booted': vm['booted'],
                                        'ip_addr': _ip_addr,
                                        'operating_system': vm['operating_system'],
                                        'hostname': vm['hostname'],
                                        'domain': vm['domain'],
                                        'built_from_iso': vm['built_from_iso'],
                                        'built_from_ova': vm['built_from_ova'],
                                        'label': vm['label']})
    return dict(vms_dict)


def get_vm_source_properties(cfg: OnApp2VHIConfig, vm_idn: str) -> Dict:
    """
    Get Virtual Machine HV IP address
    :param vm_idn:
    :return:
    """
    onapp_requests = OnAppRequests(cfg)
    vm_properties = onapp_requests.get(f'virtual_machines/{vm_idn}')['virtual_machine']
    network_info = get_vm_network_info(cfg, vm_identifier=vm_idn)
    _vm_hv_id = vm_properties['hypervisor_id']
    _vm_os = vm_properties['operating_system']
    _hot_migrate = vm_properties['allowed_hot_migrate']
    _vm_hostname = vm_properties['hostname']
    _vm_domain = vm_properties['domain']
    _hv_props = onapp_requests.get(f'settings/hypervisors/{_vm_hv_id}')
    _vm_hv_ip = _hv_props['hypervisor']['ip_address']
    _vm_nics = onapp_requests.get(f'virtual_machines/{vm_idn}/ip_addresses')
    _vm_ip_addr = [nic['ip_address_join']['ip_address']['address'] for nic in _vm_nics
                   if nic['ip_address_join']['ip_address']][0]
    logs.info(f"-- Hypervisor ID: {_vm_hv_id} | Hypervisor IP ADDRESS: {_vm_hv_ip} | VM IP ADDRESS {_vm_ip_addr}")
    return {'hv_ip': _vm_hv_ip, 'vm_os': _vm_os, 'vm_ip_addr': _vm_ip_addr, 'network_info': network_info,
            'hot_migrate': _hot_migrate, 'hostname': _vm_hostname, 'domain': _vm_domain}


def get_bucket_limits(cfg: OnApp2VHIConfig, bucket_id: str) -> dict:
    """
        Get Compute Zone and Data Store Zone limitations from the specific bucket
        :param bucket_id: "1", "1000"
        :return: peaks of the limits
    """
    compute_zones_in_bucket, datastore_zones_in_bucket = [], []
    access_controls = _get_onapp_bucket_access_controls(cfg, f'{bucket_id}')

    for ac in access_controls:
        if ac['access_control']['type'] == 'compute_zone_resource' \
                and ac['access_control']['server_type'] == 'virtual':
            # float("inf") represents infinity
            ram_quota = float("inf") if ac['access_control']['limits']['limit_memory'] is None \
                else int(ac['access_control']['limits']['limit_memory'])
            cpu_quota = float("inf") if ac['access_control']['limits']['limit_cpu'] is None \
                else int(ac['access_control']['limits']['limit_cpu'])

            compute_zones_in_bucket.append(ComputeZone(name=ac['access_control']['target_name'],
                                                       cpu=cpu_quota,
                                                       ram=ram_quota))
        elif ac['access_control']['type'] == 'data_store_zone_resource':
            # float("inf") represents infinity
            quota = float("inf") if ac['access_control']['limits']['limit'] is None \
                else int(ac['access_control']['limits']['limit'])
            datastore_zones_in_bucket.append(DataStoreZone(name=ac['access_control']['target_name'],
                                                           storage_policy=quota))
        else:
            continue

    max_vCPUs = max([v.cpu for v in compute_zones_in_bucket])
    max_RAM = max([v.ram for v in compute_zones_in_bucket])
    max_storage_policy = max([v.storage_policy for v in datastore_zones_in_bucket])
    # -1 represents infinity on the VHI side
    return {"cores": -1 if max_vCPUs == float("inf") else max_vCPUs,
            "ram-size": -1 if max_RAM == float("inf") else max_RAM * (1024 ** 3),
            "storage": -1 if max_storage_policy == float("inf") else max_storage_policy}


def _get_onapp_nics_per_vm(cfg: OnApp2VHIConfig, vm_idn: str) -> List[NIC]:
    """
    Returns list of NICs per Virtual Server
    """
    logs.info(f'{_spaces}-- OnApp: Get OnApp VM NICs  --')
    onapp_requests = OnAppRequests(cfg)
    response = onapp_requests.get(f'virtual_machines/{vm_idn}/network_interfaces')

    nics = [NIC(id=nic['network_interface']['id'],
                vm_id=nic['network_interface']['virtual_machine_id'],
                label=nic['network_interface']['label'],
                nic_idn=nic['network_interface']['identifier'],
                is_primary=nic['network_interface']['primary'],
                mac=nic['network_interface']['mac_address'],
                network_join=nic['network_interface']['network_join_id'],
                default_firewall_rule=nic['network_interface']['default_firewall_rule'],
                is_connected=nic['network_interface']['connected'],
                ip_addr=_get_nic_ip_address(cfg, vm_idn=vm_idn, network_interface_id=nic['network_interface']['id']))
            for nic in response]
    return [] if not nics else nics


def _get_nic_ip_address(cfg: OnApp2VHIConfig, vm_idn: str, network_interface_id: str) -> str:
    """
    Return the IP address for the specified NIC.
    """
    logs.info(f'{_spaces}-- OnApp: Get OnApp VM NIC IP address  --')
    onapp_requests = OnAppRequests(cfg)
    response = onapp_requests.get(f'virtual_machines/{vm_idn}/ip_addresses')
    for nic in response:
        if nic['ip_address_join']['network_interface_id'] == network_interface_id:
            return nic['ip_address_join']['ip_address']['address']


def get_vm_firewall_rules(cfg: OnApp2VHIConfig, vm_idn: str) -> List[FirewallRules]:
    """
    Returns list of all firewall rules for all NICs
    """
    logs.info(f'{_spaces}-- OnApp: Get OnApp VM Firewall Rules  --')
    onapp_requests = OnAppRequests(cfg)
    version = onapp_version(cfg)
    response = onapp_requests.get(f'virtual_machines/{vm_idn}/firewall_rules')
    firewall_rules = []
    for fr in response:
        comment = ''
        if version > 6.0:
            comment = fr['firewall_rule']['comment']
        firewall_rules.append(FirewallRules(id=fr['firewall_rule']['id'],
                                            position=fr['firewall_rule']['position'],
                                            address=fr['firewall_rule']['address'],
                                            command=fr['firewall_rule']['command'],
                                            port=fr['firewall_rule']['port'],
                                            protocol=fr['firewall_rule']['protocol'],
                                            nic_id=fr['firewall_rule']['network_interface_id'],
                                            comment=comment,
                                            source_port=fr['firewall_rule']['source_port'],
                                            destination_ip=fr['firewall_rule']['destination_ip'],
                                            protocol_type=fr['firewall_rule']['protocol_type']))
    return [] if not firewall_rules else firewall_rules


def get_primary_nic(cfg: OnApp2VHIConfig, vm_idn: str) -> NIC:
    """
    Returns primary NIC, otherwise, this functions returns None
    """
    for nic in _get_onapp_nics_per_vm(cfg, vm_idn):
        if nic.is_primary:
            return nic


def get_firewall_rules_for_specific_nic(nic: NIC, rules: List[FirewallRules]) -> List[FirewallRules]:
    """
    Returns firewall rules for specific NIC
    """
    return [rule for rule in rules if rule.nic_id == nic.id]


def check_user_role(user_data: dict) -> str:
    """
    Check whether user has admin role or not
    :param user_data:
    :return:
    """
    admin_role = ''
    for role in user_data['roles']:
        if not role:
            continue

        if role['role']['identifier'] == "admin" or len(role['role']['permissions']) >= 162:
            admin_role = True
            break
        else:
            admin_role = False
    return admin_role


def transfer_firewall_rules_to_sg(cfg: OnApp2VHIConfig,
                                  vm_idn: str,
                                  vhiproj: str,
                                  drop: str = "DROP",
                                  accept: str = "ACCEPT"):
    """
    Transfer firewall rules to the VHI side from OnApp
    :param vm_idn: "843yjosames"
    :param vhiproj: "5ae5cee8-677e-4ed6-b1cb-b9e9bb4c36f7"
    :param drop: "DROP"
    :param accept: "ACCEPT"
    :return:
    """
    sgr_data = {"ethertype": "IPv4"}  # VHI only supports IPv4, so this variable hardcoded
    sg = VinfraSecurityGroups(cfg)
    sgr = VinfraSGRules(cfg)
    proj = VinfraProject(cfg)

    primary_nic = get_primary_nic(cfg, vm_idn=vm_idn)
    if not primary_nic:
        logs.warn("Primary network interface not found!")
        return False

    firewall_rules_for_vm = get_vm_firewall_rules(cfg, vm_idn=vm_idn)
    firewall_rules_for_primary_nic = get_firewall_rules_for_specific_nic(nic=primary_nic, rules=firewall_rules_for_vm)
    security_group_name = f'sg_from_vs_{vm_idn}_and_nic_{primary_nic.nic_idn}'
    _, output = proj.show(domain=cfg.vhi_conf['vinfra_domain'], project_name=vhiproj)
    proj_id = json.loads(output)['id']
    _, sg_list = sg.list_security_group(**{'project': proj_id})
    sg_list = json.loads(sg_list)
    if not firewall_rules_for_primary_nic:
        logs.debug(msg='No rules for transfer!')
        for sg in sg_list:
            if sg['name'] == 'default':
                # return only default security group ID
                return sg['id']

    # Verify whether SC exists on VHI side
    if len(sg_list) > 1:
        for _sg_obj in sg_list:
            if security_group_name != _sg_obj['name']:
                continue

            logs.warn(f'Security Group exists on VHI side NAME: {_sg_obj["name"]}| ID: {_sg_obj["id"]}')
            return _sg_obj['id']

    # Create new SG
    _description = f'Security group created from the VS: {vm_idn} with primary NIC: {primary_nic.nic_idn}'
    _cmd_create_sg = (f"{cfg.DOMAIN_AUTH} --vinfra-domain='{cfg.vhi_conf['vinfra_domain']}' --vinfra-project='{vhiproj}'"
                      f" service compute security-group create {security_group_name} --description '{_description}'")
    _, sg_create = sg.execute(_cmd_create_sg)
    sg_create = json.loads(sg_create)
    sg_name = sg_create.get('name', '')
    _, output = sg.list_security_group(**{'name': f"{sg_name}"})
    output = json.loads(output)
    if not output:
        logs.error(msg="Security group hasn't been created")
        return False

    custom_sg_id = output[0]['id']

    # https://virtuozzo.atlassian.net/wiki/spaces/PROD/pages/2616033301/WiP+-+Compare+OnApp+firewall+rules+with+Virtuozzo+security+groups#The-first-scenario%3A-The-default-firewall-rule-of-OnApp-VS-is-Drop
    accept_only_rules = [rule for rule in firewall_rules_for_primary_nic if rule.command == accept]
    if primary_nic.default_firewall_rule in (drop, accept) and accept_only_rules:
        for rule in accept_only_rules:
            logs.debug(f"Rule position is: {rule.position}")
            data = copy.deepcopy(sgr_data)
            data["protocol"] = rule.protocol
            data["remote-ip"] = rule.address
            if rule.port:  # some protocols do not need to specify ports
                if len(rule.port.split(',')) > 1:  # some rules contain multiple ports
                    for port in list(set(rule.port.split(','))):  # iterate by unique ports only.
                        data["port-range-min"] = port
                        data["port-range-max"] = port

                        _, output = sgr.create(sg_name=sg_name, **data)
                        output = json.loads(output)
                else:
                    data["port-range-min"] = rule.port
                    data["port-range-max"] = rule.port
                    # create the rule
                    _, output = sgr.create(sg_name=sg_name, **data)
                    output = json.loads(output)
            if not output:
                logs.warn(msg=f"Firewall rule: {rule} was not transferred correctly")
        if primary_nic.default_firewall_rule == accept:
            _, output = sgr.create(sg_name=sg_name, **{"ethertype": "IPv4",
                                                       "port-range-min": 1,
                                                       "port-range-max": 65535,
                                                       "remote-ip": '0.0.0.0/0'})
            output = json.loads(output)
            if not output:
                logs.warn(msg="All Accept rule: '0.0.0.0/0' was not set correctly.")

        _, output = sg.list_security_group(**{'name': f"{sg_name}"})
        custom_sg_id = json.loads(output)[0]['id']
        logs.debug(f"Transferred firewall rules list: {custom_sg_id} for newly created Security group")
        return custom_sg_id
    else:
        logs.debug(f'Firewall rules contains only {accept}" rules.')
        return custom_sg_id


def get_iface_from_specific_vs(cfg: OnApp2VHIConfig, vm_name: str):
    """
    Get iface from specific VS
    """
    vsi = VinfraServerInterface(cfg)

    _, output = vsi.list_server(server_name=vm_name)
    ifaces = json.loads(output)
    if not ifaces:
        return False

    return ifaces[0]['id']


def attach_security_group_to_nic_and_enable_spoofing(cfg: OnApp2VHIConfig,
                                                     vm_name: str,
                                                     iface: str,
                                                     sg_id: str):
    """
    Attach SG to the specific NIC and enable spoofing
    """
    vsi = VinfraServerInterface(cfg)

    if not sg_id:
        logs.error('*** Security Group has not been attached to NIC. Please check logs. ***')
        return False

    if not iface:
        logs.error('*** Iface has NOT been found. Please check logs. ***')
        return False

    _, output = vsi.set(vm_name=vm_name, iface=iface, spoofing=True, **{'security-group': sg_id})
    logs.info(iface)
    iface = json.loads(output)
    logs.debug(iface)


class VmHandler:
    WINDOWS_OS = 'windows'
    LINUX_OS = 'linux'

    def __init__(self, **kwargs):
        self._booted = kwargs.get("booted", "")
        self._ip_addr = kwargs.get("ip_addr", "")
        self._os = kwargs.get("operating_system", "")
        self._user = 'root' if self._os == self.LINUX_OS else 'Administrator'
        self.guest_tools_result = ''
        self.vz_guest_tools = ''
        self.cloud_init = ''

    def vm_handler(self):
        """
        Handle virtual machine status whether it booted or not, and check OS
        :return:
        """
        from onapp2vhi.ops.cold_migrate import vm_cold_migrate
        from onapp2vhi.ops.live_migrate import vm_live_migrate
        from onapp2vhi.ops.install_bootloader import vm_install_bootloader
        from onapp2vhi.ops.install_bootloader_offline import vm_install_bootloader_offline
        from onapp2vhi.ops.install_win_drivers import vm_install_win_drivers
        from onapp2vhi.ops.install_win_drivers_offline import vm_install_win_drivers_offline
        from onapp2vhi.inc.helper import Helper
        if self._booted:
            _cmd = (f'timeout 150s ssh {Helper.SSH_OPTS.value} -p 22'
                    f' {self._user}@{self._ip_addr} -t "hostname; exit;"')
            (rc, ou) = ssh_run(command=_cmd)
            if not rc:
                if self._os == self.WINDOWS_OS:
                    return vm_install_win_drivers, vm_live_migrate
                else:
                    return vm_install_bootloader, vm_live_migrate
            else:
                return False, False
        else:
            if self._os == self.WINDOWS_OS:
                return vm_install_win_drivers_offline, vm_cold_migrate
            else:
                return vm_install_bootloader_offline, vm_cold_migrate


class GenerateXmlConfig:
    RECOVERY_TEMPLATE = 'ls /onapp/tools/recovery/recovery-centos-7.*.{file} | tail -1'

    def __init__(self, cfg: OnApp2VHIConfig, config_path: str, vm_idn: str, hv_ip: str):
        """
        Generates Recovery .xml file for VM
        :param vm_idn:
        :param hv_ip:
        """
        self._vm_idn = vm_idn
        self._hv_ip = hv_ip
        self._kernel = 'kernel'
        self._iso = 'iso'
        self._initrd = 'initrd'
        self._config_path = config_path
        self._recovery_mg_file = join(self._config_path, 'recovery.xml.mg')
        self._recovery_xml = join(self._config_path, 'recovery.xml')
        self.hv_ssh = SSH(**{"host": hv_ip, 'ssh_key': cfg.ssh_key})

    def shut_down_vm(self):
        """
        Shut down VM and save original xml and remove cdrom
        :return:
        """
        cmd_1 = (f"virsh dumpxml {self._vm_idn} 2>/dev/null > /tmp/{self._vm_idn}.xml;"
                 f" cat /tmp/{self._vm_idn}.xml' 2>/dev/null")
        exit_status, vm_xml_cfg = self.hv_ssh.execute(command=cmd_1)
        vm_xml = KVMxml.fromstring(vm_xml_cfg)
        for device in vm_xml.findall("devices"):
            for disk in device.findall("disk"):
                if disk.attrib['device'] == "cdrom":
                    device.remove(disk)
        xmltree = KVMxml.ElementTree(vm_xml)
        _file = join(self._config_path, f"{self._vm_idn}.xml")
        logs.info(f"Writing config into {_file}", separator=True)
        xmltree.write(_file)
        exit_status, vm_xml_cfg = self.hv_ssh.execute(command=f'virsh shutdown {self._vm_idn}')
        from time import sleep
        for i in range(0, 100):
            if exit_status != 1:
                break

            sleep(10)
            exit_status, vm_xml_cfg = self.hv_ssh.execute(command=f'virsh dominfo {self._vm_idn}')
        sleep(5)

    def generate_recovery_xml_config(self, primary_disk: str):
        """
        Generate recovery config xml based on HV parameters
        Grep .iso, .kernel, .initrd files and set them into recovery file on the fly
        :param primary_disk: "/dev/disk3s4"
        :return:
        """
        logs.info(f"{_spaces}-- OnApp: Get Hypervisor Recovery Info --", header=True)
        exit_status, iso = self.hv_ssh.execute(self.RECOVERY_TEMPLATE.format(file=self._iso))
        exit_status, kernel = self.hv_ssh.execute(self.RECOVERY_TEMPLATE.format(file=self._kernel))
        exit_status, initrd = self.hv_ssh.execute(self.RECOVERY_TEMPLATE.format(file=self._initrd))
        tree = KVMxml.parse(self._recovery_xml)
        root = tree.getroot()
        for device in root.findall("devices"):
            for disk in device.findall("disk"):
                if disk.attrib['type'] == "block":
                    for source in disk.findall('source'):
                        source.attrib['dev'] = primary_disk
                elif disk.attrib['type'] == "file":
                    source = disk.findall('source')
                    if 'recovery-centos-7.' in source[0].attrib['file']:
                        source[0].attrib['file'] = iso.strip('\n')
        if root[8][1].tag == 'kernel':
            root[8][1].text = kernel.strip('\n')
        if root[8][2].tag == 'initrd':
            root[8][2].text = initrd.strip('\n')
        tree.write(self._recovery_mg_file)


def get_disk_type(cfg: OnApp2VHIConfig, vm_idn: str) -> str:
    """
    Deactivate primary disk
    :param vm_idn: 'i43oijf8sdu'
    :return:
    """
    logs.info(f"{_spaces}-- OnApp: GET DISK TYPE for VM {vm_idn} --", header=True)
    _onapp_disks = get_onapp_vm_disks(cfg, vm_idn)
    ovm_dsk = [_disk for _disk in _onapp_disks if _disk['primary']][0]
    disk_type = ovm_dsk['datastore_type']
    logs.info(f'Disk type is: {disk_type.upper()}')
    return disk_type


def activate_disk(cfg: OnApp2VHIConfig, vm_idn: str, vm_ohv_ip: str, multiply_disks=False, disk=None):
    """
    Activate primary disk
    :param vm_idn: 'i43oijf8sdu'
    :param vm_ohv_ip: '10.120.0.7'
    :param multiply_disks: True or False
    :param disk: {disk: info}
    :return:
    """
    logs.info(f"{_spaces}-- OnApp: HV ACTIVATING DISK --", header=True)
    hv_ssh = SSH(**{"host": vm_ohv_ip, 'ssh_key': cfg.ssh_key})
    ovm_dsk = disk
    ds_type = None
    store_idn = None
    disk_idn = None
    if not multiply_disks:
        _onapp_disks = get_onapp_vm_disks(cfg, vm_idn)
        ovm_dsk = [_disk for _disk in _onapp_disks if _disk['primary']][0]
        store_idn = ovm_dsk['datastore_idn']
        disk_idn = ovm_dsk['disk_idn']
        ds_type = ovm_dsk['datastore_type']
    elif multiply_disks:
        store_idn = ovm_dsk['datastore_idn']
        disk_idn = ovm_dsk['disk_idn']
        ds_type = ovm_dsk['datastore_type']
    if ds_type == 'is':
        # Here We are working on Hypervisor side Port is 22 and HV IP
        logs.debug(f'{_spaces}-- OnApp HV: get frontend UUID')
        exit_status, output = hv_ssh.execute(command='onappstore getid')
        try:
            frontend_uuid = re.findall('\d+', re.findall('uuid=\d+', output)[0])[0]
        except IndexError:
            logs.error(f"The UUID was not found. Output:\n\t{output}")
            return False

        # Get Disk Info
        logs.debug(f'{_spaces}-- OnApp HV: Get Disk Info')
        exit_status, output = hv_ssh.execute(command=f'onappstore diskinfo uuid={disk_idn}')
        try:
            disk_status = re.search(r"\bstatus=(\d+)", output)
            status = int(disk_status.group(1))
        except IndexError:
            logs.error(f"The status was not found. Output:\n\t{output}")
            return False

        # If disk is offline, activate it
        logs.debug(msg=f'Disk Status: {status}', separator=True)
        if not status:
            hv_ssh.execute(command=f'onappstore online uuid={disk_idn} frontend_uuid={frontend_uuid}')
        return True

    elif ds_type == 'lvm':
        hv_ssh.execute(command=f'lvchange -ay /dev/{store_idn}/{disk_idn}')
        return True


def deactivate_disk(cfg: OnApp2VHIConfig, vm_idn: str, vm_ohv_ip: str, **kwargs):
    """
    Deactivate primary disk
    :param vm_idn: Virtual Machine ID 'i43oijf8sdu'
    :param vm_ohv_ip: VM IP addr '10.120.0.7'
    :param kwargs: {}
    :return:
    """

    hv_ssh = SSH(**{"host": vm_ohv_ip, 'ssh_key': cfg.ssh_key})
    if not kwargs:
        _onapp_disks = get_onapp_vm_disks(cfg, vm_idn)
        ovm_dsk = [_disk for _disk in _onapp_disks if _disk['primary']][0]
        disk_idn = ovm_dsk['disk_idn']
        ds_type = ovm_dsk['datastore_type']
    else:
        disk_idn = kwargs.get('disk_idn', '')
        ds_type = kwargs.get('datastore_type', '')
    if ds_type == 'lvm':
        if not kwargs:
            onappvm_primary_disk = get_onapp_vm_disks(cfg, vm_idn=vm_idn, primary=True)
        else:
            onappvm_primary_disk = kwargs.get('path', '')
        logs.info(f"{_spaces}-- OnApp: HV DEACTIVATING DISK [{onappvm_primary_disk}|{ds_type}] --", header=True)
        exit_status, output = hv_ssh.execute(command=f'lvchange -an {onappvm_primary_disk}')
        if not exit_status_code_handler(exit_code=exit_status, message=f'Disk deactivation failed. Output\n\t{output}'):
            return False

        return True

    elif ds_type == 'is':
        logs.info(f"{_spaces}-- OnApp: HV DEACTIVATING DISK [{disk_idn}|{ds_type}] --", header=True)
        exit_status, output = hv_ssh.execute(command=f'onappstore offline uuid={disk_idn}')
        if not exit_status_code_handler(exit_code=exit_status, message=f'Disk deactivation failed. Output\n\t{output}'):
            return False

        return True


def create_new_vhi_vm(cfg: OnApp2VHIConfig,
                      vhi_ssh: SSH,
                      vinfra_access: str,
                      vm_idn: str,
                      network: str,
                      vhi_image: str,
                      onapp_disks: list,
                      flavour: str,
                      onapp_nics: list,
                      hostname: str,
                      domain: str,
                      vhi_storage_policy: str):
    """
    Create new VM on VHI side with the same properties as at OnApp
    Disks and Networks
    :param vhi_ssh: object ssh connector
    :param vinfra_access: str - vinfra properties to access
    :param vm_idn: str "Wrv34vt6n"
    :param network: str "public2"
    :param vhi_image: str "linux"
    :param onapp_disks: list [{"size": 5}, {. . .}]
    :param flavour: str "flavor_1_128"
    :param onapp_nics: list [{"ips": ["0.0.0.0", "1.1.1.1"], "mac": "MAC-Addr"}, {. . .}]
    :param hostname: "virtual_server"
    :param domain: "domain"
    :param vhi_storage_policy: "default"
    :return: str VHI VM ID: "3647dfe-ewr34v3rg4b-34tgfbvdzfjh"
    """
    _vhi_vm_id = ''
    hostname_domain = f'{hostname}.{domain}'.lower()
    onappvm_pri_ips = onapp_nics[0]['ips']
    create_cmd = (f"{vinfra_access} service compute server create '{hostname_domain}'"
                  f" --description '{hostname_domain}_{vm_idn}' {network} --volume source=image,id={vhi_image},"
                  f"size={onapp_disks[0]['size']},storage-policy={vhi_storage_policy}"
                  f" --flavor {flavour} -f json | jq -r \".id\"")
    exit_status, output = vhi_ssh.execute(command=create_cmd)
    if 'INTERNAL SERVER ERROR' in output:
        logs.error(f'*** SOMETHING WENT WRONG. MIGRATION FAILED DUE TO ERROR:\n{Bcolors.BOLD}{output}{Bcolors.ENDC}\n'
                   f'Last running command:\n{Bcolors.WARN}{create_cmd}{Bcolors.ENDC}\n\n'
                   f'{Bcolors.FAIL}Please check VHI services.{Bcolors.ENDC}')
        return False

    if not exit_status and output:
        # ToDo - need to add verification step whether VM created successfully
        _vhi_vm_id = output.strip("\n")
        logs.info(f"NEW VHI VM CREATED: {cfg.vhi_conf['url']}/compute/servers/instances/{_vhi_vm_id}", separator=True)
        logs.info(f"{_spaces}...STOPPING VM BEFORE MIGRATION...")
        exit_status, output = vhi_ssh.execute(
            f"for ((i=1;i<=100;i++)); do {vinfra_access} service compute server stop {_vhi_vm_id} --hard --wait"
            f" --timeout 15 -f json | jq -r -c [.name,.id,.vm_state,.power_state,.status] ;  "
            f"pwstate=\"`{vinfra_access} service compute server show {_vhi_vm_id} -f json | jq -r .power_state `\" ; "
            f"echo \"$pwstate\" ; if [[ \"$pwstate\" == \"SHUTDOWN\" ]];"
            f" then break; fi ; sleep 1; done 2>/dev/null",
            real_data=True
        )
        if not exit_status_code_handler(exit_code=exit_status,
                                        message=f'VM is not created. Output:\n\t{output}'):
            return False

    if len(onapp_disks) > 1:
        logs.info("-- VHI: Create and Attach extra VHI VM's disks --")
        for idx, dsk in enumerate(onapp_disks):
            if idx >= 1:
                exit_status, output = vhi_ssh.execute(
                    f"{vinfra_access} service compute volume create --size {dsk['size']} "
                    f"onapp-{_vhi_vm_id} --storage-policy default -f json | jq -c -r \".id\""
                )
                new_disk_id = output.strip()
                exit_status, output = vhi_ssh.execute(
                    f"{vinfra_access} service compute server volume attach "
                    f"--server {_vhi_vm_id} {new_disk_id} -f json | jq -c 2>/dev/null"
                )
                if not exit_status_code_handler(exit_code=exit_status,
                                                message=f'VM volume is not attached. Output:\n\t{output}'):
                    return False

    if len(onappvm_pri_ips) > 1:
        logs.info(f"{_spaces}-- VHI: allocate and assign extra VHI VM's IP addresses to primary NIC--")
        _ips_params = ''
        for ip in onappvm_pri_ips:
            _ips_params += f"--fixed-ip ip-address={ip} "
        exit_status, output = vhi_ssh.execute(f"{vinfra_access} service compute server iface "
                                              f"list --server {_vhi_vm_id} -f json | jq -c -r .[0].id 2>/dev/null")
        _vhi_nic0_id = output.strip()
        exit_status, output = vhi_ssh.execute(
            f"{vinfra_access} service compute server iface set {_ips_params} --server "
            f"{_vhi_vm_id} {_vhi_nic0_id} -f json | jq -c -r .fixed_ips 2>/dev/null"
        )
        if not exit_status_code_handler(exit_code=exit_status,
                                        message=f'VM iface is not set. Output:\n\t{output}'):
            return False

    return _vhi_vm_id


DEFAULT_ONAPP_USER_NAMES = ('system_owner', 'cloud_locations_manager')


def prepare_vhi_migration_data(cfg: OnApp2VHIConfig, user_idn=None):
    """
    This method prepare user data and vm data for VHI migration
    :param user_idn:
    :return:
    """
    # Get User data and Virtual Servers from OnApp
    if user_idn and type(user_idn) == int:
        _user_data = get_user_data(cfg, url=f"users/{user_idn}", get_type='ID')
        _vms_dict = get_all_virtual_machines(cfg, user_id=user_idn)
    else:
        _user_data = get_user_data(cfg,
                                   url='users',
                                   get_type='',
                                   value_to_search=None,
                                   all_users=True)
        _vms_dict = get_all_virtual_machines(cfg)
    if not _user_data:
        return False

    if not _vms_dict:
        return False

    vhi_users_data = []

    # Prepare data from OnApp to VHI
    for _user_info in _user_data:
        user_password = generate_random_password()
        _user = _user_info['user']
        login = _user['login']
        if login in DEFAULT_ONAPP_USER_NAMES:
            continue

        if '.' in login:
            login = login.replace('.', '_')

        elif 'admin' == login:
            login = 'onapp_admin'

        _vhi_user_data = {'user_email': _user['email'],
                          'id': _user['id'],
                          'first_name': _user['first_name'],
                          'last_name': _user['last_name'],
                          'password': user_password,
                          'roles': _user['roles'],
                          'user_login': f'{login}',
                          'project_name': f"project_{_user['email']}",
                          'quotas': get_bucket_limits(cfg, bucket_id=_user['bucket_id']),
                          'virtual_machines': []}
        if user_idn and _vms_dict:
            _vhi_user_data['virtual_machines'] = _vms_dict[user_idn]
            vhi_users_data.append(_vhi_user_data)
            continue

        elif _vms_dict:
            for user_id, vms_list in _vms_dict.items():
                if _vhi_user_data['id'] != user_id:
                    continue

                _vhi_user_data['virtual_machines'] = vms_list
        vhi_users_data.append(_vhi_user_data)
    return vhi_users_data


def onapp_version(cfg: OnApp2VHIConfig, full=None):
    """
    Get OnApp version
    {
        "version": "6.7.0-19"
    }
    :param full: set to True to get "6.7.0-19" minor version
    :return:
    """
    onapp_requests = OnAppRequests(cfg)

    onap_version_resp = onapp_requests.get("version")
    version = float(onap_version_resp['version'][:3])
    logs.info(msg=f"{_spaces} -- OnApp Version [{onap_version_resp['version']}] --", header=True)
    if full:
        version = onap_version_resp['version']
    return version


def suspend_vm(cfg: OnApp2VHIConfig, vm_id: str):
    """
    Suspend VM
    :param vm_id: "jcubtlkttnknax"
    :return:
    """
    logs.debug(msg=f'{_spaces}-- Suspending VM [{vm_id}] --')
    onapp_requests = OnAppRequests(cfg)
    response = onapp_requests.post(route=f'virtual_machines/{vm_id}/suspend', data={})
    return response
