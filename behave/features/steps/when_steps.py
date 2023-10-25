from fabric import Connection
from fixtures.helper import helper
from time import sleep
import json

CHECK_FAILED = False

use_step_matcher('parse')
@when('I delete the {entity} ({name}) in Onapp cloud')
def step_impl(context, entity, name):

    entity_plural = helper.convert_to_plural(helper.rephrase_key(entity))
    entity_singular = helper.convert_to_singular(helper.rephrase_key(entity))
    fixture = helper.get_fixture(entity_singular)

    label = fixture[name][entity_singular]["label"]

    response = {}

    data = context.cp.search(entity_plural, args=label)

    # we proceed with the step even if the vm is not found
    if not data:
        pass

    else:
        id = data[0][helper.convert_to_singular(entity_plural)]["id"]
        response[entity_plural] = context.cp.delete(entity_plural, id)

        context.response = response[entity_plural]

use_step_matcher('re')
@when('I create a? (?P<entity>[\w\s]+) \((?P<name>[\w\W\s]+)\) in VHI portal with following details')
def step_impl(context, entity, name):

    entity = helper.rephrase_key(entity)
    data = helper.get_fixture(entity)[name]

    headings = helper.vinfra_rephrase_key(context.table.headings)
    for heading in headings:
        for row in context.table.rows:
            row.headings = headings
            data[heading] = row[heading]

    print(data)

    param = ""

    for key, value in data.items():
        if key not in ["name", "isolated_type"]:
            param += "--" + key + " " + value + " " 

    config = helper.get_config()
    
    # add the related entity in future, currently it only supports storage policy
    if entity == "storage_policy":
        _ = helper.open_vhi_ssh_connection(config["vhi"], "service compute storage-policy create {param} {name}".format(param=param, name=data["name"]))
        context.entity_to_delete["storage_policy"] = {"name": data["name"]}

    elif entity == "placement":
        _ = helper.open_vhi_ssh_connection(config["vhi"], "service compute placement create --{isolated_type} {param} {name}"\
                                           .format(isolated_type=data["isolated_type"], param=param, name=data["name"]))
        
        context.entity_to_delete["placement"] = {"name": data["name"], "nodes": data["nodes"]}

use_step_matcher('re')
@when('I create a? (?P<entity>[\w\s]+) \((?P<name>[\w\W\s]+)\) with following details')
def step_impl(context, entity, name):

    entity = helper.rephrase_key(entity)
    entity_plural = helper.convert_to_plural(entity)
    data = helper.get_fixture(entity)[name]

    headings = helper.rephrase_key(context.table.headings)
    for heading in headings:
        for row in context.table.rows:
            row.headings = headings
            data[entity][heading] = row[heading]

    print(data)

    if entity == "network":
        entity = "settings/" + entity_plural
    else:
        entity = entity_plural

    context.response = context.cp.create(entity=entity, data=data)

use_step_matcher('re')
@when('I create a? (?P<entity>[\w\s]+) \((?P<name>[\W\w\s]+)\)')
def step_impl(context, entity, name):
    
    entity = helper.rephrase_key(entity)
    config = helper.get_fixture(entity)
    data = config[name]

    if entity == "virtual_machine":
        if data["virtual_machine"].get("template_id"):
            search_query = "search_filter[query]=" + data["virtual_machine"]["template_id"].replace(" ", "+")
            data["virtual_machine"]["template_id"] = context.cp.search_with_search_filter("templates", search_query)[0]["image_template"]["id"]

        if data["virtual_machine"].get("hypervisor_id"):
            # there is no search function for a particular hypervisor
            hv_list = context.cp.get_all("hypervisors")
            match = False

            for hv in hv_list:
                if hv["hypervisor"]["label"].strip() == data["virtual_machine"].get("hypervisor_id"):
                    data["virtual_machine"]["hypervisor_id"] = hv["hypervisor"]["id"]
                    match = True
                    break

            if not match:
                assert CHECK_FAILED, "error: HV is not found"

    if entity == "network":
        entity = "settings/" + helper.convert_to_plural(entity)

        if data["network"].get("network_group_id"):
            data["network"]["network_group_id"] = context.cp.search("settings/network_zones", args=data["network"]["network_group_id"])[0]["network_group"]["id"]
    else:
        entity = helper.convert_to_plural(entity)

    print(data)

    if entity == "settings/networks":

        arr_get_network = context.cp.search("settings/networks", args=data["network"]["label"])
        
        if not arr_get_network:
            context.response = context.cp.create(entity=entity, data=data)
        else:
            print("network is not created in onapp cloud as it has been created earlier")

        network_identifier = context.cp.search("settings/networks", args=data["network"]["label"])[0]["network"]["identifier"]

        # to create a network that contains ipv4 and ipv6
        if "ipv4-ipv6" in name:
            # hardcode on getting ipv6 from yaml
            # this is used to resolve the issue where ipv6 cannot be created automatically using migration script
            vhi_network = "behave-network-vhi-ipv6"
            vhi_config = helper.get_config()["vhi"]

            command = "create network_{network_identifier} --physical-network {physical_network} --cidr {cidr} --gateway {gateway} --allocation-pool {allocation_pool} --vlan {vlan} --no-dhcp" \
                .format(network_identifier=network_identifier, physical_network=config[vhi_network]["physical-network"], cidr=config[vhi_network]["cidr"], \
                        gateway=config[vhi_network]["gateway"], allocation_pool=config[vhi_network]["allocation-pool"], vlan=config[vhi_network]["vlan"])
            
            print(command)
            _ = helper.open_vhi_ssh_connection(vhi_config, "service compute network %s" % command)
            sleep(60)

            vhi_network= "behave-network-vhi-ipv4"

            command = "create --network network_{network_identifier} --cidr {cidr} --gateway {gateway} --allocation-pool {allocation_pool} --no-dhcp" \
                .format(network_identifier=network_identifier, cidr=config[vhi_network]["cidr"], \
                        gateway=config[vhi_network]["gateway"], allocation_pool=config[vhi_network]["allocation-pool"])
            
            print(command)
            _ = helper.open_vhi_ssh_connection(vhi_config, "service compute subnet %s" % command)
            sleep(60)

        # to create a network with ipv6 only
        elif "ipv6" in name:
            # hardcode on getting ipv6 from yaml
            # this is used to resolve the issue where ipv6 cannot be created automatically using migration script
            vhi_network = "behave-network-vhi-ipv6"
            vhi_config = helper.get_config()["vhi"]

            command = "create network_{network_identifier} --physical-network {physical_network} --cidr {cidr} --gateway {gateway} --allocation-pool {allocation_pool} --vlan {vlan} --no-dhcp" \
                .format(network_identifier=network_identifier, physical_network=config[vhi_network]["physical-network"], cidr=config[vhi_network]["cidr"], \
                        gateway=config[vhi_network]["gateway"], allocation_pool=config[vhi_network]["allocation-pool"], vlan=config[vhi_network]["vlan"])
            
            print(command)
            _ = helper.open_vhi_ssh_connection(vhi_config, "service compute network %s" % command)
            sleep(60)

        context.arr_network_to_delete.append(network_identifier)
        context.entity_to_delete["network"] = context.arr_network_to_delete
        
    else:
        context.response = context.cp.create(entity=entity, data=data)

use_step_matcher('parse')
@when('I add a new ip net ({ip_net}) to network ({network})')
def step_impl(context, ip_net, network):

    data = helper.get_fixture("ip_net")[ip_net]

    if hasattr(context, "response"):
        if context.response.json().get("network"):
            network_id = context.response.json()["network"]["id"]
        else:
            assert CHECK_FAILED, "error: network is not found"

    else:
 
        network_label = helper.get_fixture("network")[network]["network"]["label"]
        network_id = context.cp.search("settings/networks", args=network_label)[0]["network"]["id"]

    arr_get_ip_net = context.cp.get("settings/networks", network_id, action="ip_nets")
    
    match = False
    for _ip_net in arr_get_ip_net:
        if _ip_net["ip_net"]["label"] == data["ip_net"]["label"]:
            match = True
            break
    
    if not match:
        context.response = context.cp.post_action("settings/networks", network_id, "ip_nets", data=data)
    else:
        print("ip net is not created as it is found within the network")

use_step_matcher('parse')
@when('I add the network join ({network_join}) from network ({network}) to the compute zone ({compute_zone})')
def step_impl(context, network_join, network, compute_zone):

    data = helper.get_fixture("network_join")[network_join]
    arr_compute_zones = context.cp.search("settings/hypervisor_zones")

    match = False
    for _compute_zone in arr_compute_zones:
        if _compute_zone["hypervisor_group"]["label"].lower() == compute_zone.lower():
            compute_zone_id = _compute_zone["hypervisor_group"]["id"]
            match = True
            break
    
    if not match:
        assert CHECK_FAILED, "error: compute zone is not found"

    arr_get_hv_network_join = context.cp.get("settings/hypervisor_zones", compute_zone_id, action="network_joins")

    match = False
    for _network_join in arr_get_hv_network_join:

        if _network_join["network_join"]["interface"] == data["network_join"]["interface"]:
            match = True
            break

    if not match:

        if hasattr(context, "response"):

            network_id = vars(context.response.request)["url"].split("/")[5]
            data["network_join"]["network_id"] = network_id

        else:
            
            network_label = helper.get_fixture("network")[network]["network"]["label"]
            arr_get_network = context.cp.search("settings/networks", args=network_label)
    
            if not arr_get_network:
                assert CHECK_FAILED, "error: network is not found"
            else:
                data["network_join"]["network_id"] = arr_get_network[0]["network"]["id"]

        context.response = context.cp.post_action("settings/hypervisor_zones", compute_zone_id, "network_joins", data=data)
    else:
        print("not attaching the network to the compute zone as it has been attached to the compute zone earlier")

use_step_matcher('parse')
@when('I add a network interface ({network_interface}) with network join ({network_join}) at compute zone ({hv}) to the virtual machine ({vm})')
def step_impl(context, network_interface, network_join, hv, vm):
    
    data = helper.get_fixture("network_interface")[network_interface]
    arr_compute_zones = context.cp.search("settings/hypervisor_zones")

    match = False
    for _compute_zone in arr_compute_zones:
        if _compute_zone["hypervisor_group"]["label"].lower() == hv.lower():
            compute_zone_id = _compute_zone["hypervisor_group"]["id"]
            match = True
            break
    
    if not match:
        assert CHECK_FAILED, "error: compute zone is not found"

    arr_network_join = context.cp.get("settings/hypervisor_zones", compute_zone_id, action="network_joins")
    fixture_network_join = helper.get_fixture("network_join")[network_join]
    
    match = False
    for _network_join in arr_network_join:
        if _network_join["network_join"]["interface"] == fixture_network_join["network_join"]["interface"]:
            network_join_id = _network_join["network_join"]["id"]
            data["network_interface"]["network_join_id"] = network_join_id
            match = True
            break

    if not match:
        assert CHECK_FAILED, "error: network join is not found"

    vm_label = helper.get_fixture("virtual_machine")[vm]["virtual_machine"]["label"]
    arr_get_vm = context.cp.get_all("virtual_machines")
    
    match = False
    for _vm in arr_get_vm:
        if _vm["virtual_machine"]["label"] == vm_label:
            vm_id = _vm["virtual_machine"]["id"]
            match = True
            break

    if not match:
        assert CHECK_FAILED, "error: virtual machine is not found"

    context.response = context.cp.post_action("virtual_machines", vm_id, "network_interfaces", data=data)

use_step_matcher('parse')
@when('I add an IP address ({ip_net}) from network ({network}) to the network interface ({network_interface}) on virtual machine ({vm})')
def step_impl(context, ip_net, network, network_interface, vm):

    if not context.response.json().get("network_interface"):
        
        _vm_label = helper.get_fixture("virtual_machine")[vm]["virtual_machine"]["label"]
        vm_id = context.cp.search("virtual_machines", args=_vm_label)[0]["virtual_machine"]["id"]

        _network_interface_label = helper.get_fixture("network_interface")[network_interface]["network_interface"]["label"]
        arr_get_network_interface = context.cp.get_all("virtual_machines/%s" % vm_id, action="network_interfaces")
        
        match = False
        for nic in arr_get_network_interface:
            if nic["network_interface"]["label"] == _network_interface_label:
                network_interface_id = nic["network_interface"]["id"]
                match = True
                break

        if not match:
            assert CHECK_FAILED, "error: network interface is not found within the vm"

    else:

        vm_id = context.response.json()["network_interface"]["virtual_machine_id"]
        network_interface_id = context.response.json()["network_interface"]["id"]

    ip_net_label = helper.get_fixture("ip_net")[ip_net]["ip_net"]["label"]
    network_label = helper.get_fixture("network")[network]["network"]["label"]

    arr_network = context.cp.get_all("settings/networks")

    for network in arr_network:
        if network["network"]["label"] == network_label:
            network_id = network["network"]["id"]
            break

    arr_ip_net = context.cp.get_all("settings/networks/%s/ip_nets" % network_id)

    for _ip_net in arr_ip_net:
        if _ip_net["ip_net"]["label"] == ip_net_label:
            ip_net_id = _ip_net["ip_net"]["id"]
            break

    if not "network_id" in locals() or not "ip_net_id" in locals():
        assert CHECK_FAILED, "error: network id is not found"

    # in our case, we always assume the first ip range
    ip_ranges = context.cp.get("settings/networks/%s/ip_nets" % network_id, ip_net_id, action="ip_ranges")

    if not ip_ranges:
        assert CHECK_FAILED, "error: no ip range is found within the network"
    else:
        ip_range_id = ip_ranges[0]["ip_range"]["id"]

    data = {"ip_address": {"network_interface_id": network_interface_id, "ip_net_id": ip_net_id, "ip_range_id": ip_range_id, "ip_version": ip_net[-1]}}
    
    print(data)
    sleep(10)
    context.response = context.cp.post_action("virtual_machines", vm_id, "ip_addresses", data=data)

use_step_matcher('parse')
@when('I {action} the virtual machine ({vm}) in Onapp cloud')
def step_impl(context, action, vm):

    vm_label = helper.get_fixture("virtual_machine")[vm]["virtual_machine"]["label"]
    arr_get_vm = context.cp.get_all("virtual_machines")
    
    match = False
    for _vm in arr_get_vm:
        if _vm["virtual_machine"]["label"] == vm_label:
            vm_id = _vm["virtual_machine"]["id"]
            match = True
            break

    if not match:
        assert CHECK_FAILED, "error: virtual machine is not found"

    context.response = context.cp.post_action("virtual_machines", vm_id, action)

def get_tool_output(output):
    '''
    output:
    ...
    ...
    [2023-05-03 09:07:20,296] INFO                     -- LIST ONAPP VIRTUAL MACHINES --
    [2023-05-03 09:07:20,296] INFO     
    +------------------------------------------------------------------------------------------------------------+
    | ID  | LABEL          | IP_ADDRESS        | IDENTIFIER     | TEMPLATE_LABEL              | BOOTED | USER_ID |
    +------------------------------------------------------------------------------------------------------------+
    | 120 | rh-vm-c7-9     | 10.119.0.8        | quoiymwhatyhyi | CentOS 7.9 x64              | False  | 4       |
    | 119 | rh-vm-ubuntu   | 10.119.0.20       | bxutwpgjpnxszl | Ubuntu 16.04 x64            | False  | 4       |
    +------------------------------------------------------------------------------------------------------------+
    '''

    table = vars(output)["stderr"]
    arr_table = table.split("\n")
        
    '''
    arr_table:
    [...,
    ...,
    '\x1b[32m[2023-05-03 09:02:47,947] INFO    \x1b[0m \x1b[32m                -- LIST ONAPP VIRTUAL MACHINES --\x1b[0m',
    '\x1b[32m[2023-05-03 09:02:47,948] INFO    \x1b[0m \x1b[32m',
    '+------------------------------------------------------------------------------------------------------------+',
    '| ID  | LABEL          | IP_ADDRESS        | IDENTIFIER     | TEMPLATE_LABEL              | BOOTED | USER_ID |',
    '+------------------------------------------------------------------------------------------------------------+',
    '| 120 | rh-vm-c7-9     | 10.119.0.8        | quoiymwhatyhyi | CentOS 7.9 x64              | False  | 4       |',
    '| 119 | rh-vm-ubuntu   | 10.119.0.20       | bxutwpgjpnxszl | Ubuntu 16.04 x64            | False  | 4       |',
    '+------------------------------------------------------------------------------------------------------------+\x1b[0m',
    '']
    '''

    count = 1
    found = False

    for row in arr_table:
        # look for row that contains "ID", it contains headers, do not loop after that
        if "ID" in row:
            arr_header = row.lower().split("|")
            found = True
            break
        count += 1

    if not found:
        assert CHECK_FAILED, "error: no data found, please check if the user exists or if the user has VM listed in Onapp cloud"

    arr_data_row = []
    for i in range(count + 1, len(arr_table) - 2):
        data = arr_table[i].split("|")
        arr_data_row.append(data)
        
    arr_header_formatted = []
    for row in arr_header:
        if row.strip() != '':
            arr_header_formatted.append(row.strip())
                    
    arr_data_row_formatted = []
    for arr in arr_data_row:
        arr_single_row = []
        for i in range(len(arr) - 1):
            if arr[i].strip() != '':
                arr_single_row.append(arr[i].strip())
        arr_data_row_formatted.append(arr_single_row)
        
    dict_data_from_tool = {}
    x = 1
    for arr in arr_data_row_formatted:
        dict_data_from_tool[x] = {}
        
        for i in range(len(arr)):
            dict_data_from_tool[x][arr_header_formatted[i]] = arr[i]
        x += 1

    return dict_data_from_tool

def get_tool_command(type, user_id=None, header=None):

    if "VM" in type:
        command = "list-onapp-vms "
    else:
        command = "list-onapp-users "

    if user_id:
        if "VM" in type:
            command += "--find=\"user_id={user_id}\" ".format(user_id=user_id)
        else:
            command += "--find=\"id={user_id}\" ".format(user_id=user_id)

    if header:
        command += "--props={header}".format(header=header)

    return command

def get_cloud_data(context, type, user_id=None, username=None):

    if user_id:
        if "VM" in type:
            data = context.cp.search_with_search_filter("virtual_machines", "search_filter[user_id]=%d" % user_id)
        else:
            data = context.cp.search("users", args=username)

    else:
        if "VM" in type:
            data = context.cp.get_all("virtual_machines")
        else:
            data = context.cp.get_all("users")
            data_copy = data

            # we do not get users without roles
            for d in data_copy:
                if not d["user"]["roles"]:
                    data.remove(d)

            del data_copy

    return data

use_step_matcher('re')
@when('I view the (?P<type>VMs?|users?) in Onapp cloud using migration tool for user \((?P<username>[\w\s]+)\)')
def step_impl(context, type, username):
    
    user = context.cp.search("users", args=username)
    if user:
        user_id = user[0]["user"]["id"]
    else:
        assert CHECK_FAILED, "error: user (%s) is not found" % username

    config = helper.get_config()
    command = get_tool_command(type, user_id=user_id)
    output = helper.open_onapp_ssh_connection(config["onapp"], command)
    dict_data_from_tool = get_tool_output(output)

    context.data = {}
    context.data["tool"] = dict_data_from_tool

    data_from_cloud = get_cloud_data(context, type, user_id=user_id, username=username)

    if data_from_cloud:
        context.data["onapp_cloud"] = data_from_cloud
    else:
        assert CHECK_FAILED, "error: no {type} found".format(type=type)


use_step_matcher('re')
@when('I view the (?P<type>VMs?|users?) in Onapp cloud using migration tool')
def step_impl(context, type):

    config = helper.get_config()

    command = get_tool_command(type)
    output = helper.open_onapp_ssh_connection(config["onapp"], command)
    dict_data_from_tool = get_tool_output(output)

    context.data = {}
    context.data["tool"] = dict_data_from_tool

    data_from_cloud = get_cloud_data(context, type)

    if data_from_cloud:
        context.data["onapp_cloud"] = data_from_cloud
    else:
        assert CHECK_FAILED, "error: no {type} found".format(type=type)

use_step_matcher('re')
@when('I view the (?P<type>VMs?|users?) in Onapp cloud using migration tool for user \((?P<username>[\w\s]+)\) with following headers')
def step_impl(context, type, username):
    
    user = context.cp.search("users", args=username)
    if user:
        user_id = user[0]["user"]["id"]
    else:
        assert CHECK_FAILED, "error: user (%s) is not found" % username

    str_header = ''
    for heading in context.table.headings:
        for row in context.table.rows:
            str_header += row[heading] + ","

    str_header = str_header[:-1]

    config = helper.get_config()
    command = get_tool_command(type, user_id=user_id, header=str_header)
    output = helper.open_onapp_ssh_connection(config["onapp"], command)
    dict_data_from_tool = get_tool_output(output)

    context.data = {}
    context.data["tool"] = dict_data_from_tool

    data_from_cloud = get_cloud_data(context, type, user_id=user_id, username=username)

    if data_from_cloud:
        context.data["onapp_cloud"] = data_from_cloud
    else:
        assert CHECK_FAILED, "error: no {type} found".format(type=type)

use_step_matcher('re')
@when('I view the (?P<type>VMs?|users?) in Onapp cloud using migration tool with following headers')
def step_impl(context, type):
    
    str_header = ''
    for heading in context.table.headings:
        for row in context.table.rows:
            str_header += row[heading] + ","

    str_header = str_header[:-1]

    config = helper.get_config()
    command = get_tool_command(type, header=str_header)
    output = helper.open_onapp_ssh_connection(config["onapp"], command)
    dict_data_from_tool = get_tool_output(output)

    context.data = {}
    context.data["tool"] = dict_data_from_tool

    data_from_cloud = get_cloud_data(context, type)

    if data_from_cloud:
        context.data["onapp_cloud"] = data_from_cloud
    else:
        assert CHECK_FAILED, "error: no {type} found".format(type=type)

use_step_matcher('re')
@when('I view the users in Onapp cloud using migration tool by using (?P<type>email|login) \((?P<data>[\w\W\s\S]+)\)')
def step_impl(context, type, data):

    data_from_cloud = context.cp.search("users", args=data)

    if not data_from_cloud:
        assert CHECK_FAILED, "error: user (%s) is not found" % data

    config = helper.get_config()
    command = "list-onapp-users --find=\"{type}={data}\"".format(type=type, data=data)

    output = helper.open_onapp_ssh_connection(config["onapp"], command)
    dict_data_from_tool = get_tool_output(output)

    context.data = {}
    context.data["tool"] = dict_data_from_tool
    context.data["onapp_cloud"] = data_from_cloud

def get_config_ini(arr_properties):

    config = helper.get_config()
    data = {}

    conn_onapp = Connection(host=config["onapp"]["host"], user=config["onapp"]["user"], port=config["onapp"]["port"], forward_agent=True)
    
    with conn_onapp.cd(config["onapp"]["migration_tool_dir"]):
            
        try:
            if "exists" in vars(conn_onapp.run("test -f config.ini && echo config.ini exists"))["stdout"]:
                user_config = "config.ini"

        except:
            user = vars(conn_onapp.run("whoami", hide=True))["stdout"].replace("\n","")
            user_config = "/home/{user}/.config/onapp2vhi/config.ini".format(user=user)

            if "exists" in vars(conn_onapp.run("test -f " + user_config + " && echo '{user_config} exists'".format(user_config=user_config)))["stdout"]:
                user_config = user_config

        for item in arr_properties:

            data[item] = vars(conn_onapp.run("echo $(awk -F \"=\" '/{item} / {{print $2}}' {user_config})"\
                                             .format(item=item, user_config=user_config), hide=True))["stdout"].replace("\n", "")

    return data

use_step_matcher('parse')
@when('I migrate the virtual machine ({name}) with following details')
def step_impl(context, name):
    
    user = context.cp.search("users", args=vars(vars(context.cp)["auth"])["username"])
    
    if user:
        user_id = user[0]["user"]["id"]
    else:
        assert CHECK_FAILED, "error: no user found"
    
    fixture = helper.get_fixture("virtual_machine")
    vm = context.cp.search("virtual_machines", args=fixture[name]["virtual_machine"]["label"])
    
    if vm:
        vm_identifier = vm[0]["virtual_machine"]["identifier"]
    else:
        assert CHECK_FAILED, "error: no machine found"

    config = helper.get_config()

    data = {}
    details = ""
    headings = helper.rephrase_key(context.table.headings)
    for heading in headings:
        for row in context.table.rows:
            row.headings = headings

            if helper.get_actual_name(heading):
                data[heading] = helper.get_fixture(heading)[row[heading]]["name"]
            elif heading == "username":
                user_id = context.cp.search("users", args=row[heading])[0]["user"]["id"]
            else:
                data[heading] = row[heading]

    basic_command = "migrate --vm {vm_id} --user {user_id} ".format(vm_id=vm_identifier, user_id=user_id)

    for key, value in data.items():
        details += "--" + key + " " + value + " "

    if hasattr(context, "log_path"):
        command = context.log_path + basic_command + details
    else:
        command = basic_command + details
    
    print(command)

    if "negative" not in context.tags:
        _ = helper.open_onapp_ssh_connection(config["onapp"], command)
    
    else:
        try:
            _ = helper.open_onapp_ssh_connection(config["onapp"], command)
        except Exception:
            pass

use_step_matcher('parse')
@when('I migrate the virtual machine ({name})')
def step_impl(context, name):

    user = context.cp.search("users", args=vars(vars(context.cp)["auth"])["username"])
    
    if user:
        user_id = user[0]["user"]["id"]
    else:
        assert CHECK_FAILED, "error: no user found"
    
    fixture = helper.get_fixture("virtual_machine")
    vm = context.cp.search("virtual_machines", args=fixture[name]["virtual_machine"]["label"])
    
    if vm:
        vm_identifier = vm[0]["virtual_machine"]["identifier"]
    else:
        assert CHECK_FAILED, "error: no machine found"

    config = helper.get_config()
    
    if hasattr(context, "log_path"):
        command = context.log_path + "migrate --vm {vm_id} --user {user_id}".format(vm_id=vm_identifier, user_id=user_id)
    else:
        command = "migrate --vm {vm_id} --user {user_id}".format(vm_id=vm_identifier, user_id=user_id)
    
    print(command)
    _ = helper.open_onapp_ssh_connection(config["onapp"], command)

use_step_matcher('parse')
@when('I delete the virtual machine ({name}) in VHI portal')
def step_impl(context, name):

    fixture = helper.get_fixture("virtual_machine")
    hostname = fixture[name]["virtual_machine"]["hostname"]
    
    config = helper.get_config()
    output = helper.open_vhi_ssh_connection(config["vhi"], "service compute server list -f json")
    vm_list = json.loads(output.stdout)

    match = False
    for vm in vm_list:

        if hostname in vm["name"]:
            match = True

            _ = helper.open_vhi_ssh_connection(config["vhi"], "service compute server delete {vm_name}".format(vm_name=vm["name"]))
            break
    
    # we proceed with the rest of the steps even if the vm is not found
    if not match:
        pass

use_step_matcher('parse')
@when('I delete the existing user account ({name}) from the VHI portal')
def step_impl(context, name):

    # read config.ini (O2V-51) in onapp CP server to extract the vinfra_domain
    config = helper.get_config()["vhi"]
    data = get_config_ini(["vinfra_domain"])
    
    # delete the user in VHI portal
    email = helper.get_fixture("user")[name]["email"]
    users = helper.open_vhi_ssh_connection(config, "domain user list --domain {vinfra_domain} -f json".format(vinfra_domain=data["vinfra_domain"]))
    arr_user = json.loads(users.stdout)

    username = ""
    for user in arr_user:
        if user["email"] == email:
            username = user["name"]
            break
    
    if username:
        _ = helper.open_vhi_ssh_connection(config, "domain user delete --domain {vinfra_domain} {username}"
                                            .format(vinfra_domain=data["vinfra_domain"], username=username))
    else:
        print("user is not found in VHI portal, proceeding with the test...")
    
use_step_matcher('parse')
@when('I set the logging path ({path})')
def step_impl(context, path):
    
    command = "--log-output-path " + path + " "
    context.log_path = command

    config = helper.get_config()

    conn = Connection(host=config["onapp"]["host"], user=config["onapp"]["user"], port=config["onapp"]["port"], forward_agent=True)
    
    with conn.cd(config["onapp"]["migration_tool_dir"]):

        try:
            # to ensure there is no folder created before
            if "exists" in vars(conn.run("test -d {path} && echo {path}/ exists".format(path=path)))["stdout"]:
                conn.run("rm -rf %s/" % path)
        except:
            print("existing %s/ is not found, proceeding..." % path)

use_step_matcher('re')
@when('I assign the storage policy \((?P<name>[\w\W\s]+)\) with (?P<size>[\d]+[M|MiB|G|GiB|T|TiB|P|PiB|E|EiB]) to the project')
def step_impl(context, name, size):

    # size is needed because vinfra does not support unlimited
    storage_policy = helper.get_fixture("storage_policy")[name]["name"]
    data = get_config_ini(["vinfra_domain", "vinfra_project"])
    config = helper.get_config()["vhi"]

    # to get project ID
    output = helper.open_vhi_ssh_connection(config, "domain project list --domain {domain} -f json".format(domain=data["vinfra_domain"]))
    project_list = json.loads(output.stdout)

    for project in project_list:
        if project["name"] == data["vinfra_project"]:
            output = helper.open_vhi_ssh_connection(config, "service compute quotas update --storage-policy {name}:{size} {project_id}"\
                                                    .format(name=storage_policy, size=size, project_id=project["id"]))
            
            break

use_step_matcher('re')
@when('I assign the placement \((?P<name>[\w\W\s]+)\) with (?P<size>[\d]+) placement to the project')
def step_impl(context, name, size):

    # size is needed because vinfra does not support unlimited
    placement_name = helper.get_fixture("placement")[name]["name"]
    data = get_config_ini(["vinfra_domain", "vinfra_project"])
    config = helper.get_config()["vhi"]

    # to get project ID
    output = helper.open_vhi_ssh_connection(config, "domain project list --domain {domain} -f json".format(domain=data["vinfra_domain"]))
    project_list = json.loads(output.stdout)

    # to get placement ID
    placement_output = helper.open_vhi_ssh_connection(config, "service compute placement list -f json")
    placement_list = json.loads(placement_output.stdout)

    for placement in placement_list:
        if placement["name"] == placement_name:
            placement_id = placement["id"]
            break

    for project in project_list:
        if project["name"] == data["vinfra_project"]:
            output = helper.open_vhi_ssh_connection(config, "service compute quotas update --placement {id}:{size} {project_id}"\
                                                    .format(id=placement_id, size=size, project_id=project["id"]))
            
            break
