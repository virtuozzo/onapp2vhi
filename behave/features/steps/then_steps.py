from fixtures.helper import helper
from time import sleep
import json

CHECK_FAILED = False # to replace buggy context.failed
TIMEOUT = 120

use_step_matcher('parse')
@then('CP API ({action}) should return status code {status_code}')
def step_impl(context, action, status_code):
    
    if hasattr(context, 'response'):
        if context.response.status_code != int(status_code):
            assert CHECK_FAILED, "error: status code returned is {actual}, with error message: {error}"\
                .format(actual=str(context.response.status_code), error=context.response.text)

use_step_matcher('re')
@then('I wait for (?P<wait_time>[0-9]+) (?P<frequency>minutes?|seconds?)')
def step_impl(context, wait_time, frequency):
    
    if "minute" in frequency:
        sleep(int(wait_time) * 60)
    else:
        sleep(int(wait_time))

use_step_matcher('parse')
@then('the virtual machine ({name}) is built successfully')
def step_impl(context, name):

    fixture = helper.get_fixture("virtual_machine")
    data = context.cp.search("virtual_machines", args=fixture[name]["virtual_machine"]["label"])

    if not data:
        assert CHECK_FAILED, "error: virtual machine is not found"

    if not data[0]["virtual_machine"]["built"] or data[0]["virtual_machine"]["state"] == "failed" or data[0]["virtual_machine"]["locked"]:
        assert CHECK_FAILED, "error: virtual machine is not built successfully"
    
    # to delete the vm in vhi portal with the vm IP found in onapp cloud
    arr_ip = []

    for ip in data[0]["virtual_machine"]["ip_addresses"]:
        arr_ip.append(ip["ip_address"]["address"])

    config = helper.get_config()
    output = helper.open_vhi_ssh_connection(config["vhi"], "service compute server list -f json")
    vm_list = json.loads(output.stdout)

    # we do nothing if the ip is not in the list
    # else we delete the vm
    for vm in vm_list:
        for network in vm["networks"]:
            for ip in network["ips"]:
                
                if ip in arr_ip:
                    _ = helper.open_vhi_ssh_connection(config["vhi"], "service compute server delete {vm_name}".format(vm_name=vm["name"]))
                    break

    # used for other verification
    context.result = data

use_step_matcher('re')
@then('I should see the (?:VM|user) listed is tally with the (?:VMs?|users?) displayed in Onapp cloud')
def step_impl(context):
    
    if len(context.data["tool"]) != len(context.data["onapp_cloud"]):
        assert CHECK_FAILED, "error: result is not tally"

use_step_matcher('re')
@then('I should see the (?:VM|user) listed has the following headers')
def step_impl(context):

    arr_header = []
    for heading in context.table.headings:
        for row in context.table.rows:
            arr_header.append(row[heading])

    match = 0
    for header in arr_header:
        # we only want to get the first row of header
        if header in context.data["tool"][1].keys():
            match += 1
      
    if match != len(arr_header):
        assert CHECK_FAILED, "error: missing header(s)"

use_step_matcher('parse')
@then('I should see the virtual machine is {state} in VHI portal')
def step_impl(context, state):

    hostname = context.result[0]["virtual_machine"]["hostname"]
    ips = []

    for ip in context.result[0]["virtual_machine"]["ip_addresses"]:
        ips.append(ip["ip_address"]["address"])

    config = helper.get_config()
    output = helper.open_vhi_ssh_connection(config["vhi"], "service compute server list -f json")
    vm_list = json.loads(output.stdout)
    
    match = False
    for vm in vm_list:

        if hostname in vm["name"] and state.lower() == vm["status"].lower():

            for network in vm["networks"]:
                for ip in ips:
                    if ip in network["ips"]:
                        match = True
                        break
            
    if not match:
        assert CHECK_FAILED, "error: the virtual machine is not found in VHI portal or its state is not %s" % state

use_step_matcher('parse')
@then('the virtual machine ({name}) is deleted successfully')
def step_impl(context, name):

    config = helper.get_config()
    output = helper.open_vhi_ssh_connection(config["vhi"], "service compute server list -f json")
    vm_list = json.loads(output.stdout)

    fixture = helper.get_fixture("virtual_machine")[name]
    hostname = fixture["virtual_machine"]["hostname"]

    match = False
    for vm in vm_list:

        if hostname in vm["name"]:
            match = True
            break

    if match:
        assert CHECK_FAILED, "error: virtual machine is not deleted"

use_step_matcher('parse')
@then('the log is seen in logging path ({path})')
def step_impl(context, path):

    if not hasattr(context, "log_path"):
        assert CHECK_FAILED, "error: this step has to be used with step 'When I set the logging path (path)"

    user = context.cp.search("users", vars(vars(context.cp)["auth"])["username"])[0]["user"]
    user_id = user["id"]
    user_login = user["login"].replace(".", "_")

    # read config.ini (O2V-51) in onapp CP server to extract the vinfra_domain
    from fabric import Connection
    config = helper.get_config()

    conn = Connection(host=config["onapp"]["host"], user=config["onapp"]["user"], port=config["onapp"]["port"], forward_agent=True)
    
    with conn.cd(config["onapp"]["migration_tool_dir"]):
        if "exists" in vars(conn.run("test -f {path}/migration_logs/migration_*.log && test -f {path}/migration_logs/{user_login}/migrated_*_user_{user_id}.log && echo log exists"
                                         .format(path=path, user_login=user_login, user_id=user_id)))["stdout"]:
            
            # remove for next run
            conn.run("rm -rf {path}".format(path=path))

        else:
            assert CHECK_FAILED, "error: logs are not found in the %s" % path

    del context.log_path

use_step_matcher('parse')
@then('its volume is using the correct storage policy ({name})')
def step_impl(context, name):

    hostname = context.result[0]["virtual_machine"]["hostname"]
    config = helper.get_config()["vhi"]
    output = helper.open_vhi_ssh_connection(config, "service compute server list -f json")
    vm_list = json.loads(output.stdout)

    match = False
    for vm in vm_list:

        if hostname in vm["name"]:
            hostname = vm["name"]
            match = True
            break

    if not match:
        assert CHECK_FAILED, "error: VM is not found in VHI portal"

    output = helper.open_vhi_ssh_connection(config, "service compute server volume list --server %s -f json" % hostname)
    arr_volume = json.loads(output.stdout)
    arr_device = []

    for device in arr_volume:
        arr_device.append(device["id"])

    storage_policy_name = helper.get_fixture("storage_policy")[name]["name"]

    for id in arr_device:

        output = helper.open_vhi_ssh_connection(config, "service compute volume show %s -c storage_policy_name -f json" % id)
        output_result = json.loads(output.stdout)["storage_policy_name"]
        
        if storage_policy_name != output_result:
            assert CHECK_FAILED, "error: disk is not using the storage policy, it is using %s" % output_result
