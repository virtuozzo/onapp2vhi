import json
from collections import defaultdict
import requests
from cfg.o2v_config import OnAppAPICredentials, Helper
import xml.etree.ElementTree as KVMxml
from functions import run_command
from inc.logger import logs
from utils import parse_matrix
from collections import namedtuple


AUTH = (OnAppAPICredentials.ONAPP_USER_EMAIL.value, OnAppAPICredentials.ONAPP_USER_APIKEY.value)


######################
##-----FUNCTION-------##
##---list_onapp_vms---##
######################
def list_onapp_vms(vals='',by='',url='',verbosity=8):
    _default_jqexp = ('[ .virtual_machine.id , .virtual_machine.label, .virtual_machine.identifier ,'
                      ' .virtual_machine.template_label , .virtual_machine.booted, .virtual_machine.user_id ]')
    URL = OnAppAPICredentials.ONAPP_CP_URL.value + '/virtual_machines.json'
    if verbosity > 7:
        verbosity = 7

    if not vals and not by:
        jqexp = "jq -c '.[] | {}'".format(_default_jqexp)
    elif not vals and by:
        by_arg = by.split("=")[0]
        by_val = by.split("=")[1]
        if by_val.isdigit():
            jqexp = "jq -c '.[] | select(.virtual_machine.{by_a}=={by_v}) | {jqpex}'".format(by_a=by_arg,
                                                                                             by_v=by_val,
                                                                                             jqpex=_default_jqexp)
        elif by_val in ('true', 'false'):
            jqexp = "jq -c '.[] | select(.virtual_machine.{by_a}=={by_v}) | {jqpex}'".format(by_a=by_arg,
                                                                                             by_v=by_val,
                                                                                             jqpex=_default_jqexp)
        else:
            jqexp = "jq -c '.[] | select(.virtual_machine.{by_a}==\"{by_v}\") | {jqpex}'".format(by_a=by_arg,
                                                                                                 by_v=by_val,
                                                                                                 jqpex=_default_jqexp)
    elif vals and by:
        by_arg = by.split("=")[0]
        by_val = by.split("=")[1]
        vals_list = [".virtual_machine.{}".format(x) for x in vals.split(",")]
        if len(vals_list) == 1:
            vals_list = vals_list[0]
        vals_str = str(vals_list).replace("'", '')
        if by_val.isdigit():
            jqexp = "jq -c '.[] | select(.virtual_machine.{by_a}=={by_v}) | {jqpex}'".format(by_a=by_arg,
                                                                                             by_v=by_val,
                                                                                             jqpex=vals_str)
        elif not by_val.isdigit():
            jqexp = "jq -c '.[] | select(.virtual_machine.{by_a}==\"{by_v}\") | {jqpex}'".format(by_a=by_arg,
                                                                                                 by_v=by_val,
                                                                                                 jqpex=vals_str)
    else:
        vals_list = [".virtual_machine.{}".format(x) for x in vals.split(",")]
        vals_str = str(vals_list).replace("'", '')
        if len(vals_list) == 1:
            vals_list = vals_list[0]
            vals_str = str(vals_list).replace("'", '')
        jqexp = "jq -c '.[] | {vls}'".format(vls=vals_str)

    logs.info('{} -- LIST ONAPP VIRTUAL MACHINES --'.format(Helper.SPACES.value))
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {res_url}".format(user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value, res_url=URL) + " | {jqex}".format(jqex=jqexp)
    (rc, ou) = run_command(CMD, verbosity, 0, '')
    default_vals = ['id', 'label', 'identifier', 'template_label', 'booted', 'user_id']
    if vals:
        default_vals = vals.split(",")
    vm_list = [a.replace('[', '').replace(']', '').replace('\"', '').split(',') for a in ou.splitlines()]
    vms = parse_matrix(default_vals, vm_list)
    logs.info("\n{}".format(vms))
    return rc, ou.decode('ascii')


######################
##-----FUNCTION-------##
##---list_onapp_users---##
######################
def list_onapp_users(vals='',by='',url='',verbosity=8):

    URL = OnAppAPICredentials.ONAPP_CP_URL.value + '/users.json'

    _default_jqexp = '[ .user.id, .user.email, .user.login, .user.roles[0].role.label ]'
    if verbosity > 7:
        verbosity = 7

    if vals == "" and by == "":
        jqexp = "jq -c '.[] | {}'".format(_default_jqexp)
    elif vals == "" and by != "":
        by_arg=by.split("=")[0]
        by_val=by.split("=")[1]
        if by_val.isdigit():
            jqexp = "jq -c '.[] | select(.user.{by_a}=={by_v}) | {jqpex}'".format(by_a=by_arg,
                                                                                  by_v=by_val,
                                                                                  jqpex=_default_jqexp)
        elif not by_val.isdigit():
            jqexp = "jq -c '.[] | select(.user.{by_a}==\"{by_v}\") | {jqpex}'".format(by_a=by_arg,
                                                                                      by_v=by_val,
                                                                                      jqpex=_default_jqexp)
    elif vals != "" and by != "":
        by_arg=by.split("=")[0]
        by_val=by.split("=")[1]
        if 'roles' in vals:
            vals = vals.replace('roles', 'roles[0].role.label')
        vals_list = [".user.{}".format(x) for x in vals.split(",")]
        if len(vals_list) == 1:
            vals_list = vals_list[0]
        vals_str = str( vals_list ).replace("'",'')
        if by_val.isdigit():
            jqexp = "jq -c '.[] | select(.user.{by_a}=={by_v}) | {jqpex}'".format(by_a=by_arg,
                                                                                  by_v=by_val,
                                                                                  jqpex=vals_str)
        elif not by_val.isdigit():
            jqexp = "jq -c '.[] | select(.user.{by_a}==\"{by_v}\") | {jqpex}'".format(by_a=by_arg,
                                                                                      by_v=by_val,
                                                                                      jqpex=vals_str)
    else:
        if 'roles' in vals:
            vals = vals.replace('roles', 'roles[0].role.label')
        vals_list = [".user.{}".format(x) for x in vals.split(",")]
        if len(vals_list) == 1:
            vals_list = vals_list[0]
        vals_str = str(vals_list).replace("'", '')
        jqexp = "jq -c '.[] | {vls}'".format(vls=vals_str)

    logs.info('{} -- LIST ONAPP USERS --'.format(Helper.SPACES.value))
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {res_url}".format(user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value, res_url=URL) + " | {jqex}".format(jqex=jqexp)
    (rc, ou) = run_command(CMD, verbosity, 0, '')
    default_vals = ['id', 'email', 'login', 'roles']
    if vals:
        default_vals = vals.split(",")
        if 'roles[0].role.label' in default_vals:
            default_vals[default_vals.index('roles[0].role.label')] = 'roles'
    user_list = [a.replace('[', '').replace(']', '').replace('\"', '').split(',') for a in ou.splitlines()]
    users = parse_matrix(default_vals, user_list)
    logs.info("\n{}".format(users))
    return rc, ou.decode('ascii')


######################
##----- FUNCTION ------##
##-get_onapp_vm_nics---##
######################
def get_onapp_vm_nics(vm_idn='',verbosity=8):

    VM_IDn = vm_idn

    #--OnApp: get source VM NICs' MACs info --#

    NOTE = """ -- OnApp: get VM's MACS -- """

    URL = OnAppAPICredentials.ONAPP_CP_URL.value + "/virtual_machines/{}/network_interfaces.json".format(VM_IDn)
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | [ .network_interface[\"id\"],.network_interface[\"mac_address\"],.network_interface[\"primary\"] ] '".format(user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value, full_url=URL )
    (rc,ou) = run_command(CMD,verbosity,0,NOTE)
    API_VM_MACS = []
    for line in ou.splitlines():
        nic = json.loads(line)
        API_VM_MACS.append( { 'id': nic[0], 'mac': nic[1].encode('ascii'),'primary': nic[2] } )

    NOTE = """ -- OnApp: get VM's IP addresses -- """

    URL = OnAppAPICredentials.ONAPP_CP_URL.value + "/virtual_machines/{}/ip_addresses.json".format(VM_IDn)
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | [ .ip_address_join[\"network_interface_id\"],.ip_address_join[\"ip_address\"][\"address\"] ] '".format(user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value, full_url=URL )
    (rc,ou) = run_command(CMD,verbosity,0,NOTE)
    API_VM_IPS = defaultdict( lambda: [] )
    for line in ou.splitlines():
        nic = json.loads(line)
        if nic[0] in API_VM_IPS.keys():
            API_VM_IPS[ nic[0] ].append( nic[1].encode('ascii') )
        else:
            API_VM_IPS[ nic[0] ] = [ nic[1].encode('ascii') ]

    API_VM_NICS = []

    for idx, mac in enumerate(API_VM_MACS):
        nic_id = API_VM_MACS[idx]['id']
        API_VM_NICS.append({'id': nic_id, 'number': idx, 'mac': API_VM_MACS[idx]['mac'], 'ips': API_VM_IPS[nic_id],
                            'primary': API_VM_MACS[idx]['primary']})

    return API_VM_NICS


##########################
##------- FUNCTION -------##
##---get_onapp_vm_disks---##
##########################
def get_onapp_vm_disks(vm_idn='', verbosity=8):
    VM_IDn = vm_idn
    #--OnApp: get source VM data_stores --#
    NOTE = """ -- OnApp: get OnApp datastores -- """
    URL = OnAppAPICredentials.ONAPP_CP_URL.value + "/settings/data_stores.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | [ .data_store.id , .data_store.identifier ] '".format(user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value, full_url=URL)
    (rc,ou) = run_command(CMD,verbosity,0,NOTE)
    API_DS = {}
    for line in ou.splitlines():
        ds = json.loads(line)
        API_DS[ ds[0] ] = ds[1].encode('ascii')
    if verbosity >= 7:
        logs.info("ONAPP_DATASTORES: \n" + str(API_DS))
        logs.info("")
    # --OnApp: get source VM disks --#
    NOTE = """ -- OnApp: get VM's disks by {identifier} -- """
    URL = OnAppAPICredentials.ONAPP_CP_URL.value + "/virtual_machines/{}/disks.json".format(VM_IDn)
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | [ .disk.identifier,.disk.data_store_id,.disk.disk_size,.disk.disk_vm_number,.disk.primary,.disk.is_swap ] '".format(user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value, full_url=URL)
    (rc, ou) = run_command(CMD,verbosity,0,NOTE)
    API_VM_DISKS = []
    for line in ou.splitlines():
        dsk = json.loads(line)
        API_VM_DISKS.append( { 'disk_idn': dsk[0].encode('ascii'),'ds_id':dsk[1], 'size': dsk[2], 'number': dsk[3], 'primary': dsk[4], "is_swap": dsk[5],'path': "/dev/"+str(API_DS[dsk[1]])+"/"+str(dsk[0]),'datastore_idn': str(API_DS[dsk[1]]) } )

    return API_VM_DISKS


#########################
##------- FUNCTION -------##
##---get_onapp_vm_primary_disk---##
##########################
def get_onapp_vm_primary_disk(vm_idn='', verbosity=8):
    VM_IDn = vm_idn
    # --OnApp: get source VM data_stores --#
    URL = OnAppAPICredentials.ONAPP_CP_URL.value + "/settings/data_stores.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | [ .data_store.id , .data_store.identifier ] '".format(user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value, full_url=URL)
    (rc, ou) = run_command(CMD, verbosity, 0)
    api_ds = {}
    for line in ou.splitlines():
        ds = json.loads(line)
        api_ds[ds[0]] = ds[1].encode('ascii')
    logs.info("ONAPP_DATASTORES: \n" + str(api_ds))
    # --OnApp: get source VM disks --#
    NOTE = """ -- OnApp: get VM's disks by {identifier} -- """
    URL = OnAppAPICredentials.ONAPP_CP_URL.value + "/virtual_machines/{}/disks.json".format(VM_IDn)
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | select(.disk.primary==true) | [ .disk.identifier,.disk.data_store_id ] '".format(user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value, full_url=URL )
    (rc, ou) = run_command(CMD, verbosity, 0, NOTE)
    api_vm_primary_disk = []
    for line in ou.splitlines():
        dsk = json.loads(line)
        api_vm_primary_disk.append({'path': "/dev/"+str(api_ds[dsk[1]])+"/"+str(dsk[0])})

    return api_vm_primary_disk


def get_onapp_vm_flavor(vm_identifier):
    """
    Get ram, cpu, data store
    :param vm_identifier: "lidqtfwggohyzk"
    :return:
    """
    _url = '{}/virtual_machines/{}.json'.format(OnAppAPICredentials.ONAPP_CP_URL.value, vm_identifier)
    logs.info('GET {}'.format(_url), separator=True)
    response = requests.get(_url, auth=AUTH)
    logs.info('Response [{}]: {}'.format(response.status_code, response.json()))
    vm_props = response.json()['virtual_machine']
    return {'vcpus': vm_props['cpus'],
            'ram': vm_props['memory'],
            'name': 'onapp_flavor_{}_{}'.format(vm_props['cpus'], vm_props['memory'])}


def _get_onapp_bucket_access_controls(bucket_id):
    """
        Get access controls from the users bucket
        :param bucket_id: "1", "1000"
        :return: json of access controls
    """
    _url = '{url}/billing/buckets/{bucket_id}/access_controls.json'.format(
        url=OnAppAPICredentials.ONAPP_CP_URL.value, bucket_id=bucket_id)
    logs.info("{}-- OnApp: Get User Bucket Access Controls --   ".format(Helper.SPACES.value), separator=True)
    logs.info('GET {url}'.format(url=_url), separator=True)
    response = requests.get(_url, auth=AUTH)
    _access_controls = response.json() if response.status_code == 200 else False
    if _access_controls:
        logs.info('Response [{}]'.format(response.status_code))
        return _access_controls
    else:
        logs.error('Response [{}]: {}'.format(response.status_code, response.content))
        return _access_controls


def get_user_ssh_keys(user_data):
    """
    Get user ssh keys and return them
    :param user_data: {"id": 3, "first_name": "Test1", "last_name": "Test2", . . .}
    :return: [ssh_key1, ssh_key2]
    """
    _url = '{}/settings/ssh_keys.json'.format(OnAppAPICredentials.ONAPP_CP_URL.value)
    logs.info("{}-- OnApp: Get User SSH keys --  ".format(Helper.SPACES.value), separator=True)
    logs.info('GET {url}'.format(url=_url), separator=True)
    _ssh_keys = []
    response = requests.get(_url, auth=AUTH)
    for ssh_key in response.json():
        if ssh_key['ssh_key']['user_id'] != user_data['id']:
            continue

        _ssh_keys.append(ssh_key['ssh_key']['key'])
    logs.info('Response [{}]: {}'.format(response.status_code, _ssh_keys))
    return _ssh_keys


def get_user_data(url, get_type, value_to_search=None, all_users=False):
    """
    Get users data from OnApp platform
    :param url: /users.json or /users/1.json
    :param get_type: ID or any value in user obj
    :param value_to_search: value based on what we will find user
    :param all_users: bool True or False
    :return:
    """
    logs.info("{}-- OnApp: Get User information --  ".format(Helper.SPACES.value), separator=True)
    logs.info('GET {url}'.format(url=url), separator=True)
    response = requests.get(url, auth=AUTH)
    if response.status_code != 200:
        logs.error(response.content)
        logs.error('Credentials you are using: {creds}'.format(creds=AUTH))
        exit(1)

    if get_type == 'ID':
        return response.json()['user'], response

    if all_users:
        return response.json(), response

    for _user in response.json():
        if value_to_search in list(_user['user'].values()):
            return _user['user'], response


def get_all_virtual_machines():
    """
    Get list of all virtual machines and sort them by user ID
    :return: list of VMs
    """
    logs.info("{}-- OnApp: Get All Virtual Machines information --  ".format(Helper.SPACES.value), separator=True)
    _url = '{}/virtual_machines.json'.format(OnAppAPICredentials.ONAPP_CP_URL.value)
    logs.info('GET {}'.format(_url), separator=True)
    response = requests.get(_url, auth=AUTH)
    logs.info('Response [{}]'.format(response.status_code))

    from collections import defaultdict
    vms_dict = defaultdict(list)
    for _vm in response.json():
        vm = _vm['virtual_machine']
        if vm["vip"]:
            continue

        vms_dict[vm['user_id']].append({'id': vm['identifier'],
                                        'booted': vm['booted'],
                                        'operating_system': vm['operating_system']})
    return dict(vms_dict)


def get_bucket_limits(bucket_id):
    """
        Get Compute Zone and Data Store Zone limitations from the specific bucket
        :param bucket_id: "1", "1000"
        :return: peaks of the limits
    """

    compute_zones_in_bucket, datastore_zones_in_bucket = [], []
    ComputeZone = namedtuple('ComputeZone', 'name cpu ram')
    DataStoreZone = namedtuple('DataStoreZone', 'name storage_policy')
    access_controls = _get_onapp_bucket_access_controls("{}".format(bucket_id))

    for _ in access_controls:
        if _['access_control']['type'] == 'compute_zone_resource' \
                and _['access_control']['server_type'] == 'virtual':
            # float("inf") represents infinity
            ram_quota = float("inf") if _['access_control']['limits']['limit_memory'] is None\
                else int(_['access_control']['limits']['limit_memory'])
            cpu_quota = float("inf") if _['access_control']['limits']['limit_cpu'] is None\
                else int(_['access_control']['limits']['limit_cpu'])

            compute_zones_in_bucket.append(ComputeZone(name=_['access_control']['target_name'],
                                                       cpu=cpu_quota,
                                                       ram=ram_quota))
        elif _['access_control']['type'] == 'data_store_zone_resource':
            # float("inf") represents infinity
            quota = float("inf") if _['access_control']['limits']['limit'] is None \
                else int(_['access_control']['limits']['limit'])
            datastore_zones_in_bucket.append(DataStoreZone(name=_['access_control']['target_name'],
                                                           storage_policy=quota))
        else:
            continue

    max_vCPUs = max([v.cpu for v in compute_zones_in_bucket])
    max_RAM = max([v.ram for v in compute_zones_in_bucket])
    max_storage_policy = max([v.storage_policy for v in datastore_zones_in_bucket])
    # -1 represents infinity on the VHI side
    return {"cores": -1 if max_vCPUs == float("inf") else max_vCPUs,
            "RAM": -1 if max_RAM == float("inf") else max_RAM * (1024 ** 3),
            "storage": -1 if max_storage_policy == float("inf") else max_storage_policy * (1024 ** 3)}


def check_user_role(user_data):
    """
    Check whether user has admin role or not
    :param user_data:
    :return:
    """
    admin_role = ''
    for role in user_data['roles']:
        if role['role']['identifier'] == "admin" or len(role['role']['permissions']) >= 162:
            admin_role = True
            break
        else:
            admin_role = False
    return admin_role


class VmHandler:
    WINDOWS_OS = 'windows'
    LINUX_OS = 'linux'

    def __init__(self, **kwargs):
        self._booted = kwargs.get("booted", "")
        self._os = kwargs.get("operating_system", "")

    def vm_handler(self):
        """
        Handle virtual machine status whether it booted or not, and check OS
        :return:
        """
        from ops.cold_migrate import vm_cold_migrate
        from ops.live_migrate import vm_live_migrate
        from ops.install_bootloader import vm_install_bootloader
        from ops.install_bootloader_offline import vm_install_bootloader_offline
        from ops.install_win_drivers import vm_install_win_drivers
        from ops.install_win_drivers_offline import vm_install_win_drivers_offline
        if self._booted:
            logs.info('{}-- LIVE MIGRATION --'.format(Helper.SPACES.value))
            if self._os == self.WINDOWS_OS:
                return vm_install_win_drivers, vm_live_migrate
            else:
                return vm_install_bootloader, vm_live_migrate
        else:
            logs.info('{}-- COLD MIGRATION --'.format(Helper.SPACES.value))
            if self._os == self.WINDOWS_OS:
                return vm_install_win_drivers_offline, vm_cold_migrate
            else:
                return vm_install_bootloader_offline, vm_cold_migrate


class GenerateXmlConfig:

    RECOVERY_TEMPLATE = "ssh root@{hv_ip} 'ls /onapp/tools/recovery/recovery-centos-7.*.{file} | tail -1'"

    def __init__(self, vm_idn, hv_ip):
        self._vm_idn = vm_idn
        self._hv_ip = hv_ip
        self._verbosity = 8
        self._kernel = 'kernel'
        self._iso = 'iso'
        self._initrd = 'initrd'
        self._recovery_mg_file = 'scripts/recovery.xml.mg'
        self._recovery_xml = 'scripts/recovery.xml'

    def shut_down_vm(self):
        """
        Shut down VM and save original xml and remove cdrom
        :return:
        """
        cmd_1 = "ssh root@{hv_ip} 'virsh dumpxml {vm_idn} 2>/dev/null > /tmp/{vm_idn}.xml ;" \
                " cat /tmp/{vm_idn}.xml' 2>/dev/null".format(vm_idn=self._vm_idn, hv_ip=self._hv_ip)
        (rc, vm_xml_cfg) = run_command(cmd_1, 1, 0)
        vm_xml = KVMxml.fromstring(vm_xml_cfg)
        for device in vm_xml.findall("devices"):
            for disk in device.findall("disk"):
                if disk.attrib['device'] == "cdrom":
                    device.remove(disk)
        xmltree = KVMxml.ElementTree(vm_xml)
        _file = "scripts/{}.xml".format(self._vm_idn)
        logs.info("Writing config into {}".format(_file), separator=True)
        xmltree.write(_file)
        cmd_2 = "ssh root@{hv_ip} 'virsh shutdown {vm_idn}'".format(hv_ip=self._hv_ip, vm_idn=self._vm_idn)
        (rc, ou) = run_command(cmd_2, self._verbosity, 0)
        from time import sleep
        for i in range(0, 100):
            if rc != 1:
                break

            sleep(10)
            cmd_3 = "ssh root@{hv_ip} 'virsh dominfo {vm_idn}'".format(hv_ip=self._hv_ip, vm_idn=self._vm_idn)
            (rc, ou) = run_command(cmd_3, self._verbosity, 0)

    def generate_recovery_xml_config(self, primary_disk):
        """
        Generate recovery config xml based on HV parameters
        Grep .iso, .kernel, .initrd files and set them into recovery file on the fly
        :param primary_disk: string
        :return:
        """
        logs.info("{}-- OnApp: Get Hypervisor Recovery Info --".format(Helper.SPACES.value), separator=True)
        (rc, iso) = run_command(self.RECOVERY_TEMPLATE.format(hv_ip=self._hv_ip, file=self._iso), self._verbosity, 0)
        (rc, kernel) = run_command(self.RECOVERY_TEMPLATE.format(hv_ip=self._hv_ip, file=self._kernel),
                                   self._verbosity, 0)
        (rc, initrd) = run_command(self.RECOVERY_TEMPLATE.format(hv_ip=self._hv_ip, file=self._initrd),
                                   self._verbosity, 0)
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
