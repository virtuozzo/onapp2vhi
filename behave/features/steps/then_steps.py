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
    else:
        if not "onapp_vm" in context.entity_to_delete and not "vhi_vm" in context.entity_to_delete:
            context.entity_to_delete["onapp_vm"] = []
            context.entity_to_delete["vhi_vm"] = []
        
        context.entity_to_delete["onapp_vm"].append(data[0]["virtual_machine"]["identifier"])
        context.entity_to_delete["vhi_vm"].append(fixture[name]["virtual_machine"]["hostname"])

    if not data[0]["virtual_machine"]["built"] or data[0]["virtual_machine"]["state"] == "failed" or data[0]["virtual_machine"]["locked"]:
        
        # [20230905] we do retry every 1 minute for 10 times, or we fail it
        # this is to allocate more times for the vm build in case the environment is busy
        i = 1
        while i < 21:

            data = context.cp.search("virtual_machines", args=fixture[name]["virtual_machine"]["label"])

            if data[0]["virtual_machine"]["built"] and data[0]["virtual_machine"]["state"] != "failed" and not data[0]["virtual_machine"]["locked"]:
                break
            else:
                print("Retrying #%s/10: wait for 60s to check for VM state again" % str(i))
                i += 1
                sleep(60)
        
        else:
            data = context.cp.search("virtual_machines", args=fixture[name]["virtual_machine"]["label"])
            
            if not data[0]["virtual_machine"]["built"] or data[0]["virtual_machine"]["state"] == "failed" or data[0]["virtual_machine"]["locked"]:
                assert CHECK_FAILED, "error: virtual machine is not built successfully"
    
    # to delete the vm in vhi portal with the existing vm IP found in onapp cloud
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
    context.result[name] = data[0]

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

    hostname = helper.get_fixture("virtual_machine")[name]["virtual_machine"]["hostname"]
    domain = helper.get_fixture("virtual_machine")[name]["virtual_machine"]["domain"]
    vhi_vm_name = hostname + "." + domain

    ips = []

    for ip in context.result[name]["virtual_machine"]["ip_addresses"]:
        ips.append(ip["ip_address"]["address"])

    config = helper.get_config()

    try:
        output = helper.open_vhi_ssh_connection(config["vhi"], "service compute server show {vhi_vm_name} -f json".format(vhi_vm_name=vhi_vm_name))
        vm = json.loads(output.stdout)
    
        match = False
        arr_vhi_vm_ip = []
        
        if vm and state.lower() == vm["status"].lower():
            match = True

            for network in vm["networks"]:
                for ip in network["ips"]:
                    arr_vhi_vm_ip.append(ip)
                
        if not match:
            assert CHECK_FAILED, "error: the virtual machine is not found in VHI portal or its state is not %s" % state
    except:
        assert CHECK_FAILED, "error: virtual machine is not found in VHI portal"

    onapp_vm_ip = context.cp.get("virtual_machines", context.result[name]["virtual_machine"]["id"], action="ip_addresses")

    arr_onapp_vm_ip = []
    for ip in onapp_vm_ip:
        arr_onapp_vm_ip.append(ip["ip_address_join"]["ip_address"]["address"])

    if arr_vhi_vm_ip.sort() != arr_onapp_vm_ip.sort():
        assert CHECK_FAILED, "error: the ip(s) in onapp and vhi aren't matched"

use_step_matcher('parse')
@then('the virtual machine ({name}) should have correct storage migrated, CPU and RAM same as flavor ({flavor_name}) stated')
def step_impl(context, name, flavor_name):
    
    hostname = helper.get_fixture("virtual_machine")[name]["virtual_machine"]["hostname"]
    domain = helper.get_fixture("virtual_machine")[name]["virtual_machine"]["domain"]
    vhi_vm_name = hostname + "." + domain

    config = helper.get_config()

    try:
        raw_vm = helper.open_vhi_ssh_connection(config["vhi"], "service compute server show {vhi_vm_name} -f json".format(vhi_vm_name=vhi_vm_name))
        vm = json.loads(raw_vm.stdout)
        dict_server_spec = {}

        match = False

        if vm:

            dict_server_spec["hostname"] = vm["name"]
            dict_server_spec["ram"] = vm["flavor"]["ram"]
            dict_server_spec["vcpus"] = vm["flavor"]["vcpus"]
            dict_server_spec["volumes"] = []

            for volume in vm["volumes"]:
                dict_server_spec["volumes"].append(volume["id"])

        total_disk_size = 0
        for volume in dict_server_spec["volumes"]:
            
            raw_disk_size = helper.open_vhi_ssh_connection(config["vhi"], "service compute volume show %s -c size -f json" % volume)
            disk_size = json.loads(raw_disk_size.stdout)["size"]
            total_disk_size += disk_size

        onapp_vms = helper.get_fixture("virtual_machine")
        
        # compare vhi vm with onapp fixture
        for vm in onapp_vms:
            if onapp_vms[vm]["virtual_machine"]["hostname"] in dict_server_spec["hostname"]:

                if  context.result[name]["virtual_machine"]["operating_system"] == "linux":
                    formula = onapp_vms[vm]["virtual_machine"]["primary_disk_size"] + onapp_vms[vm]["virtual_machine"]["swap_disk_size"]
                else:
                    formula = onapp_vms[vm]["virtual_machine"]["primary_disk_size"]

                if formula == total_disk_size:

                    match = True
                    break

        if not match:
            assert CHECK_FAILED, "error: disk space aren't tally"
        
        match = False
        raw_flavor = helper.open_vhi_ssh_connection(config["vhi"], "service compute flavor show %s -f json" % flavor_name)
        flavor = json.loads(raw_flavor.stdout)

        if dict_server_spec["ram"] == flavor["ram"] and dict_server_spec["vcpus"] == flavor["vcpus"]:
            match = True
        
        if not match:
            assert CHECK_FAILED, "error: flavor used is not matched as per mentioned" 
    
    except:
        assert CHECK_FAILED, "error: virtual machine is not found"              

use_step_matcher('parse')
@then('the virtual machine ({name}) should have correct CPU, RAM and storage')
def step_impl(context, name):

    hostname = helper.get_fixture("virtual_machine")[name]["virtual_machine"]["hostname"]
    domain = helper.get_fixture("virtual_machine")[name]["virtual_machine"]["domain"]
    vhi_vm_name = hostname + "." + domain

    config = helper.get_config()

    try:
        raw_vm = helper.open_vhi_ssh_connection(config["vhi"], "service compute server show {vhi_vm_name} -f json".format(vhi_vm_name=vhi_vm_name))
        vm = json.loads(raw_vm.stdout)
        dict_server_spec = {}

        match = False
        if vm:
            dict_server_spec["hostname"] = vm["name"]
            dict_server_spec["ram"] = vm["flavor"]["ram"]
            dict_server_spec["vcpus"] = vm["flavor"]["vcpus"]
            dict_server_spec["volumes"] = []

            for volume in vm["volumes"]:
                dict_server_spec["volumes"].append(volume["id"])

        total_disk_size = 0
        for volume in dict_server_spec["volumes"]:
            
            raw_disk_size = helper.open_vhi_ssh_connection(config["vhi"], "service compute volume show %s -c size -f json" % volume)
            disk_size = json.loads(raw_disk_size.stdout)["size"]
            total_disk_size += disk_size

        onapp_vms = helper.get_fixture("virtual_machine")
        # compare vhi vm with onapp fixture
        for vm in onapp_vms:
            if onapp_vms[vm]["virtual_machine"]["hostname"] in dict_server_spec["hostname"]:

                if  context.result[name]["virtual_machine"]["operating_system"] == "linux":
                    formula = onapp_vms[vm]["virtual_machine"]["primary_disk_size"] + onapp_vms[vm]["virtual_machine"]["swap_disk_size"]
                else:
                    formula = onapp_vms[vm]["virtual_machine"]["primary_disk_size"]

                if onapp_vms[vm]["virtual_machine"]["memory"] == dict_server_spec["ram"] and \
                    onapp_vms[vm]["virtual_machine"]["cpus"] == dict_server_spec["vcpus"] and \
                    formula == total_disk_size:

                    match = True
                    break

        if not match:
            assert CHECK_FAILED, "error: some specs aren't tally"
    
    except:
        assert CHECK_FAILED, "error: virtual machine is not found"

use_step_matcher('parse')
@then('the virtual machine ({name}) is deleted successfully')
def step_impl(context, name):

    hostname = helper.get_fixture("virtual_machine")[name]["virtual_machine"]["hostname"]
    domain = helper.get_fixture("virtual_machine")[name]["virtual_machine"]["domain"]
    vhi_vm_name = hostname + "." + domain

    config = helper.get_config()

    try: 
        output = helper.open_vhi_ssh_connection(config["vhi"], "service compute server {vhi_vm_name} -f json".format(vhi_vm_name=vhi_vm_name))
        vm = json.loads(output.stdout)

        if vm:
            assert CHECK_FAILED, "error: virtual machine is not deleted"
    except:
        assert CHECK_FAILED, "error: virtual machine is not found"

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
@then('the virtual machine ({name}) is using the correct storage policy ({storage_policy}) in its volume')
def step_impl(context, name, storage_policy):

    hostname = context.result[name]["virtual_machine"]["hostname"]
    domain = context.result[name]["virtual_machine"]["domain"]
    vhi_vm_name = hostname + "." + domain

    config = helper.get_config()["vhi"]
    output = helper.open_vhi_ssh_connection(config, "service compute server volume list --server %s -f json" % vhi_vm_name)
    arr_volume = json.loads(output.stdout)
    arr_device = []

    for device in arr_volume:
        arr_device.append(device["id"])

    storage_policy_name = helper.get_fixture("storage_policy")[storage_policy]["name"]

    for id in arr_device:

        output = helper.open_vhi_ssh_connection(config, "service compute volume show %s -c storage_policy_name -f json" % id)
        output_result = json.loads(output.stdout)["storage_policy_name"]
        
        if storage_policy_name != output_result:
            assert CHECK_FAILED, "error: disk is not using the storage policy, it is using %s" % output_result

use_step_matcher('parse')
@then('the virtual machine ({name}) is placed in the corrent placement ({placement})')
def stepm_impl(context, name, placement):

    hostname = context.result[name]["virtual_machine"]["hostname"]
    domain = context.result[name]["virtual_machine"]["domain"]
    vhi_vm_name = hostname + "." + domain

    config = helper.get_config()["vhi"]
    placement_name = helper.get_fixture("placement")[placement]["name"]

    try:
        placement_output = helper.open_vhi_ssh_connection(config, "service compute placement show {placement_name} -f json".format(placement_name=placement_name))
        placement_ = json.loads(placement_output.stdout)

        if placement_:
            placement_id = placement_["id"]

    except:
        assert CHECK_FAILED, "error: placement is not found"
    
    try:
        vm_output = helper.open_vhi_ssh_connection(config, "service compute server show {vhi_vm_name} -f json".format(vhi_vm_name=vhi_vm_name))
        vm = json.loads(vm_output.stdout)
    
        match = False
        if vm:
            for p in vm["placements"]:
                if p == placement_id:
                    match = True
                    break

        if not match:
            assert CHECK_FAILED, "error: vm is not placed in correct placement"
    except:
        assert CHECK_FAILED, "error: virtual machine is not found"

use_step_matcher('parse')
@then('I should not see the virtual machine ({name}) in VHI portal')
def step_impl(context, name):

    hostname = context.result[name]["virtual_machine"]["hostname"]
    domain = context.result[name]["virtual_machine"]["domain"]
    vhi_vm_name = hostname + "." + domain

    config = helper.get_config()
    
    try:
        output = helper.open_vhi_ssh_connection(config["vhi"], "service compute server show {vhi_vm_name} -f json".format(vhi_vm_name=vhi_vm_name))
        vm = json.loads(output.stdout)
    
        if vm:
            assert CHECK_FAILED, "error: the virtual machine is found in VHI portal"

    except:
        # we do nothing if virtual machine is not found
        pass

use_step_matcher('parse')
@then('I should see the hotplug is enabled in virtual machine ({name})')
def step_impl(context, name):
    
    hostname = context.result[name]["virtual_machine"]["hostname"]
    domain = context.result[name]["virtual_machine"]["domain"]
    vhi_vm_name = hostname + "." + domain

    config = helper.get_config()
    output = helper.open_vhi_ssh_connection(config["vhi"], "service compute server show {vhi_vm_name} -f json".format(vhi_vm_name=vhi_vm_name))
    vm = json.loads(output.stdout)
    
    match = False
    if vm:
        if vm["allow_live_resize"]:
            match = True

    if not match:
        assert CHECK_FAILED, "error: hotplug is not enabled"

use_step_matcher('parse')
@then('I should see the hotplug is disabled in virtual machine ({name})')
def step_impl(context, name):
    
    hostname = context.result[name]["virtual_machine"]["hostname"]
    domain = context.result[name]["virtual_machine"]["domain"]
    vhi_vm_name = hostname + "." + domain

    config = helper.get_config()
    output = helper.open_vhi_ssh_connection(config["vhi"], "service compute server show {vhi_vm_name} -f json".format(vhi_vm_name=vhi_vm_name))
    vm = json.loads(output.stdout)
    
    match = False
    if vm:
        if not vm.get("allow_live_resize"):
            match = True

    if not match:
        assert CHECK_FAILED, "error: hotplug is not disabled"

def get_guest_tool_cloud_init(migration_log_path, onapp_vm_identifier):

    config = helper.get_config()
    data = {}

    if not migration_log_path:
        migration_log_path = "/migration_logs/"
    else:
        migration_log_path = "/" + migration_log_path.replace("--log-output-path", "").replace(" ", "") + "/migration_logs/"

    from fabric import Connection
    conn_onapp = Connection(host=config["onapp"]["host"], user=config["onapp"]["user"], port=config["onapp"]["port"], forward_agent=True)
    
    with conn_onapp.cd(config["onapp"]["migration_tool_dir"] + migration_log_path):
            
        try:
            log_exists = vars(conn_onapp.run("grep -R %s */*.log" % onapp_vm_identifier, hide=True))["stdout"]

            if log_exists:
                log_location = log_exists[0:log_exists.find(":")]

                arr_properties = ["Installation Cloud-init", "Installation vz-guest-tools"]

                for item in arr_properties:

                    if item == "Installation Cloud-init":
                        package = "cloud-init"
                    elif item == "Installation vz-guest-tools":
                        package = "guest-tools"

                    data[package] = vars(conn_onapp.run("echo $(awk -F \":\" '/{item}/ {{print $2}}' {log_location})"\
                                                     .format(item=item, log_location=log_location), hide=True))["stdout"].replace("\n", "")

        except:
            assert CHECK_FAILED, "error: there is an error in the migration path: %s" % migration_log_path

    return data

use_step_matcher('re')
@then('the virtual machine \((?P<name>[\w\W]+)\) should (?P<verb>not have|have) (?P<package>guest-tools|cloud-init) installed')
def step_impl(context, name, verb, package):

    fixture = helper.get_fixture("virtual_machine")
    vm_identifier = context.cp.search("virtual_machines", args=fixture[name]["virtual_machine"]["label"])[0]["virtual_machine"]["identifier"]

    if hasattr(context, "log_path"):
        data = get_guest_tool_cloud_init(context.log_path, vm_identifier)

    elif not hasattr(context, "log_path"):
        data = get_guest_tool_cloud_init("", vm_identifier)

    if verb == "not have":

        if data[package].lower() == "not installed":
            pass
        else:
            assert CHECK_FAILED, "error: {package} is installed".format(package=package)

    else:

        if data[package].lower() == "installed":
            pass
        else:
            assert CHECK_FAILED, "error: {package} is not installed".format(package=package)