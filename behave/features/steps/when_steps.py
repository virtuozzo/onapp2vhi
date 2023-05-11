from fabric import Connection
from fixtures.helper import cp_helper
import os
import yaml

CHECK_FAILED = False

def get_fixture(entity):

    path = os.path.dirname(os.path.abspath("fixtures/{entity}.yaml".format(entity=entity))) + "/" + entity + ".yaml"
    return yaml.load(open(path).read(), Loader=yaml.FullLoader)

def get_config():

    path = os.path.dirname(os.path.abspath("features/config.yaml")) + "/config.yaml"
    config = yaml.load(open(path).read(), Loader=yaml.FullLoader)
    return config
    
def open_ssh_connection(config, command):

    conn = Connection(host=config["host"], user=config["user"], port=config["port"], forward_agent=True)

    with conn.cd(config["migration_tool_dir"]):
        with conn.prefix("source " + config["virtual_env"]):
            output = conn.run("onapp2vhi " + command)

    return output

use_step_matcher('parse')
@when('I delete the {entity} ({name})')
def step_impl(context, entity, name):

    entity_plural = cp_helper.convert_to_plural(cp_helper.rephrase_key(entity))
    response = {}

    data = context.cp.search(entity_plural, args=name)
    if not data:
        assert CHECK_FAILED, "error: {name} is not found".format(name=name)

    id = data[0][cp_helper.convert_to_singular(entity_plural)]["id"]
    response[entity_plural] = context.cp.delete(entity_plural, id)

    context.response = response[entity_plural]

use_step_matcher('re')
@when('I create a? (?P<entity>[\w\s]+) \((?P<name>[\w\W\s]+)\) with following details')
def step_impl(context, entity, name):

    entity = cp_helper.rephrase_key(entity)
    entity_plural = cp_helper.convert_to_plural(entity)
    data = get_fixture(entity)[name]

    headings = cp_helper.rephrase_key(context.table.headings)
    for heading in headings:
        for row in context.table.rows:
            row.headings = headings
            data[entity][heading] = row[heading]

    print(data)

    context.response = context.cp.create(entity=entity_plural, data=data)

use_step_matcher('re')
@when('I create a? (?P<entity>[\w\s]+) \((?P<name>[\W\w\s]+)\)')
def step_impl(context, entity, name):
    
    entity = cp_helper.rephrase_key(entity)
    config = get_fixture(entity)
    data = config[name]

    if entity == "virtual_machine":
        if data["virtual_machine"].get("template_id"):
            search_query = "search_filter[query]=" + data["virtual_machine"]["template_id"].replace(" ", "+")
            data["virtual_machine"]["template_id"] = context.cp.search_with_search_filter("templates", search_query)[0]["image_template"]["id"]

    print(data)

    context.response = context.cp.create(entity=cp_helper.convert_to_plural(entity), data=data)

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
    for row in arr_table:
        # look for row that contains "ID", it contains headers, do not loop after that
        if "ID" in row:
            arr_header = row.lower().split("|")
            break
        count += 1

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

use_step_matcher('re')
@when('I view the VMs in Onapp cloud using migration tool for user \((?P<username>[\w\s]+)\)')
def step_impl(context, username):
    
    user = context.cp.search("users", args=username)
    if user:
        user_id = user[0]["user"]["id"]
    else:
        assert CHECK_FAILED, "error: user (%s) is not found" % username

    config = get_config()
    output = open_ssh_connection(config["onapp"], "list-onapp-vms --find=\"user_id=%s\"" % user_id)
    dict_data_from_tool = get_tool_output(output)

    context.data = {}
    context.data["tool"] = dict_data_from_tool

    data_from_cloud = context.cp.search_with_search_filter("virtual_machines", "search_filter[user_id]=%d" % user_id)

    if data_from_cloud:
        context.data["onapp_cloud"] = data_from_cloud
    else:
        assert CHECK_FAILED, "error: no VM found"


use_step_matcher('re')
@when('I view the VMs in Onapp cloud using migration tool')
def step_impl(context):

    config = get_config()
    output = open_ssh_connection(config["onapp"], "list-onapp-vms")
    dict_data_from_tool = get_tool_output(output)

    context.data = {}
    context.data["tool"] = dict_data_from_tool

    data_from_cloud = context.cp.get_all("virtual_machines")

    if data_from_cloud:
        context.data["onapp_cloud"] = data_from_cloud
    else:
        assert CHECK_FAILED, "error: no VM found"

use_step_matcher('re')
@when('I view the VMs in Onapp cloud using migration tool for user \((?P<username>[\w\s]+)\) with following headers')
def step_impl(context, username):
    
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
    
    config = get_config()
    output = open_ssh_connection(config["onapp"], "list-onapp-vms --find=\"user_id={}\" --props={}".format(user_id, str_header))
    dict_data_from_tool = get_tool_output(output)

    context.data = {}
    context.data["tool"] = dict_data_from_tool

    data_from_cloud = context.cp.search_with_search_filter("virtual_machines", "search_filter[user_id]=%d" % user_id)

    if data_from_cloud:
        context.data["onapp_cloud"] = data_from_cloud
    else:
        assert CHECK_FAILED, "error: no VM found"

use_step_matcher('re')
@when('I view the VMs in Onapp cloud using migration tool with following headers')
def step_impl(context):
    
    str_header = ''
    for heading in context.table.headings:
        for row in context.table.rows:
            str_header += row[heading] + ","

    str_header = str_header[:-1]
    
    config = get_config()
    output = open_ssh_connection(config["onapp"], "list-onapp-vms --props=%s" % str_header)
    dict_data_from_tool = get_tool_output(output)

    context.data = {}
    context.data["tool"] = dict_data_from_tool

    data_from_cloud = context.cp.get_all("virtual_machines")

    if data_from_cloud:
        context.data["onapp_cloud"] = data_from_cloud
    else:
        assert CHECK_FAILED, "error: no VM found"