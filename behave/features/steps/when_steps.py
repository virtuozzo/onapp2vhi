from fixtures.helper import helper
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

    context.response = context.cp.create(entity=entity_plural, data=data)

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
            # there is no search function for a particulaar hypervisor
            hv_list = context.cp.get_all("hypervisors")
            match = False

            for hv in hv_list:
                if hv["hypervisor"]["label"].strip() == data["virtual_machine"].get("hypervisor_id"):
                    data["virtual_machine"]["hypervisor_id"] = hv["hypervisor"]["id"]
                    match = True
                    break

            if not match:
                assert CHECK_FAILED, "error: HV is not found"

    print(data)

    context.response = context.cp.create(entity=helper.convert_to_plural(entity), data=data)

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
    command = "migrate --vm {vm_id} --user {user_id}".format(vm_id=vm_identifier, user_id=user_id)
    _ = helper.open_onapp_ssh_connection(config["onapp"], command)

use_step_matcher('parse')
@when('I delete the virtual machine ({name}) in VHI portal')
def step_impl(context, name):

    fixture = helper.get_fixture("virtual_machine")
    vm_name = fixture[name]["virtual_machine"]["hostname"]
    
    config = helper.get_config()
    output = helper.open_vhi_ssh_connection(config["vhi"], "service compute server list -f json")
    vm_list = json.loads(output.stdout)

    match = False
    for vm in vm_list:

        if vm_name == vm["name"]:
            match = True

            _ = helper.open_vhi_ssh_connection(config["vhi"], "service compute server delete {vm_name}".format(vm_name=vm_name))
            break
    
    # we proceed with the rest of the steps even if the vm is not found
    if not match:
        pass