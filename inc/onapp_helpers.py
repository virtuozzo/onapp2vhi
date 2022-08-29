import json
from collections import defaultdict
import requests
from cfg.o2v_config import OnAppAPICredentials, Helper
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
        by_arg=by.split("=")[0]
        by_val=by.split("=")[1]
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
        by_arg=by.split("=")[0]
        by_val=by.split("=")[1]
        vals_list = [ ".virtual_machine.{}".format(x) for x in vals.split(",") ]
        if len(vals_list) == 1:
            vals_list = vals_list[0]
        vals_str = str( vals_list ).replace("'",'')
        if by_val.isdigit():
            jqexp = "jq -c '.[] | select(.virtual_machine.{by_a}=={by_v}) | {jqpex}'".format(by_a=by_arg,
                                                                                             by_v=by_val,
                                                                                             jqpex=vals_str)
        elif not by_val.isdigit():
            jqexp = "jq -c '.[] | select(.virtual_machine.{by_a}==\"{by_v}\") | {jqpex}'".format(by_a=by_arg,
                                                                                                 by_v=by_val,
                                                                                                 jqpex=vals_str)
    else:
        vals_list = [ ".virtual_machine.{}".format(x) for x in vals.split(",") ]
        if len(vals_list) == 1:
            vals_list = vals_list[0]
            vals_str = str( vals_list ).replace("'", '')
        jqexp = "jq -c '.[] | {vls}'".format(vls=vals_str)

    logs.info('{} -- LIST ONAPP VIRTUAL MACHINES --'.format(Helper.SPACES.value))
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {res_url}".format(user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value, res_url=URL) + " | {jqex}".format(jqex=jqexp)
    (rc,ou) = run_command(CMD,verbosity,0,'')
    default_vals = ['id', 'label', 'identifier', 'template_label', 'booted', 'user_id']
    if vals:
        default_vals = vals.split(",")
    vm_list = [a.replace('[', '').replace(']', '').replace('\"', '').split(',') for a in ou.splitlines()]
    vms = parse_matrix(default_vals, vm_list)
    logs.info("\n{}".format(vms))
    return (rc,ou.decode('ascii'))


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
        vals_list = [ ".user.{}".format(x) for x in vals.split(",") ]
        if len(vals_list) == 1:
            vals_list = vals_list[0]
        vals_str = str( vals_list ).replace("'",'')
        jqexp = "jq -c '.[] | {vls}'".format(vls=vals_str)

    logs.info('{} -- LIST ONAPP USERS --'.format(Helper.SPACES.value))
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {res_url}".format(user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value, res_url=URL) + " | {jqex}".format(jqex=jqexp)
    (rc,ou) = run_command(CMD,verbosity,0,'')
    default_vals = ['id', 'email', 'login', 'roles']
    if vals:
        default_vals = vals.split(",")
        if 'roles[0].role.label' in default_vals:
            default_vals[default_vals.index('roles[0].role.label')] = 'roles'
    user_list = [a.replace('[', '').replace(']', '').replace('\"', '').split(',') for a in ou.splitlines()]
    users = parse_matrix(default_vals, user_list)
    logs.info("\n{}".format(users))
    return (rc,ou.decode('ascii'))


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
def get_onapp_vm_disks(vm_idn='',verbosity=8):

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

#--OnApp: get source VM disks --#

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
def get_onapp_vm_primary_disk(vm_idn='',verbosity=8):

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

#--OnApp: get source VM disks --#

    NOTE = """ -- OnApp: get VM's disks by {identifier} -- """

    URL = OnAppAPICredentials.ONAPP_CP_URL.value + "/virtual_machines/{}/disks.json".format(VM_IDn)
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | select(.disk.primary==true) | [ .disk.identifier,.disk.data_store_id ] '".format(user_email=OnAppAPICredentials.ONAPP_USER_EMAIL.value, user_apikey=OnAppAPICredentials.ONAPP_USER_APIKEY.value, full_url=URL )
    (rc,ou) = run_command(CMD,verbosity,0,NOTE)
    API_VM_PRIMARY_DISK = []
    for line in ou.splitlines():
        dsk = json.loads(line)
        API_VM_PRIMARY_DISK.append( { 'path': "/dev/"+str(API_DS[dsk[1]])+"/"+str(dsk[0]) } )

    return API_VM_PRIMARY_DISK


def get_onapp_vm_flavor(vm_identifier):
    """
    Get ram, cpu, data store
    :param vm_identifier: "lidqtfwggohyzk"
    :return:
    """
    _url = '{}/virtual_machines/{}.json'.format(OnAppAPICredentials.ONAPP_CP_URL.value, vm_identifier)
    logs.info('GET {}'.format(_url))
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
    logs.info("{}-- OnApp: Get User Bucket Rate Card --   \n".format(Helper.SPACES.value), separator=True)
    logs.info('GET {url}'.format(url=_url))
    response = requests.get(_url, auth=AUTH)
    _access_controls = response.json() if response.status_code == 200 else False
    if _access_controls:
        logs.info('Response [{}]: {}'.format(response.status_code, _access_controls))
        return _access_controls
    else:
        logs.error('Response is wrong [{}]'.format(response.status_code))
        return _access_controls


def get_user_ssh_keys(user_data):
    """
    Get user ssh keys and return them
    :param user_data: {"id": 3, "first_name": "Test1", "last_name": "Test2", . . .}
    :return: [ssh_key1, ssh_key2]
    """
    _url = '{}/settings/ssh_keys.json'.format(OnAppAPICredentials.ONAPP_CP_URL.value)
    logs.info("{}-- OnApp: Get User SSH keys --   \n".format(Helper.SPACES.value), separator=True)
    logs.info('GET {url}'.format(url=_url))
    _ssh_keys = []
    response = requests.get(_url, auth=AUTH)
    for ssh_key in response.json():
        if ssh_key['ssh_key']['user_id'] != user_data['id']:
            continue

        _ssh_keys.append(ssh_key['ssh_key']['key'])
    logs.info('Response [{}]: {}'.format(response.status_code, _ssh_keys))
    return _ssh_keys


def get_user_data(url, get_type, value_to_search=None):
    """
    Get users data from OnApp platform
    :param url: /users.json or /users/1.json
    :param get_type: ID or any value in user obj
    :param value_to_search: value based on what we will find user
    :return:
    """
    logs.info("{}-- OnApp: Get User information --   \n".format(Helper.SPACES.value), separator=True)
    logs.info('GET {url}'.format(url=url))
    response = requests.get(url, auth=AUTH)
    if response.status_code != 200:
        logs.error(response.content)
        logs.error('Credentials you are using: {creds}'.format(creds=AUTH))
        exit(1)

    if get_type == 'ID':
        return response.json()['user'], response

    for _user in response.json():
        if value_to_search in list(_user['user'].values()):
            return _user['user'], response


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
            "RAM": -1 if max_RAM == float("inf") else max_RAM,
            "storage": -1 if max_storage_policy == float("inf") else max_storage_policy}
