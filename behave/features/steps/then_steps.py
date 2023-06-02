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

    if data[0]["virtual_machine"]["built"] and data[0]["virtual_machine"]["state"] != "failed" and not data[0]["virtual_machine"]["locked"]:
        pass
    else:
        assert CHECK_FAILED, "error: virtual machine is not built successfully"
    
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
@then('I should see the virtual machine ({name}) is {state} in VHI portal')
def step_impl(context, name, state):

    hostname = context.result[0]["virtual_machine"]["hostname"]
    ips = []

    for ip in context.result[0]["virtual_machine"]["ip_addresses"]:
        ips.append(ip["ip_address"]["address"])

    config = helper.get_config()
    output = helper.open_vhi_ssh_connection(config["vhi"], "service compute server list -f json")
    vm_list = json.loads(output.stdout)
    
    match = False
    for vm in vm_list:

        if hostname in vm["name"] and state == vm["status"]:

            for network in vm["networks"]:
                for ip in ips:
                    if ip in network["ips"]:
                        match = True
                        break
            
    if not match:
        assert CHECK_FAILED, "error: the virtual machine is not found in VHI portal"

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
