from fixtures.helper import helper
from time import sleep
import json

def after_scenario(context, scenario):
    
    if "migrate_vm" in context.feature.tags:
        
        # onapp cloud
        entity_plural = "virtual_machines"
        entity_singular = "virtual_machine"

        if "cold_migration" in context.feature.tags and "linux" in context.feature.tags:
            name = "linux-vm-without-startup"

        elif "cold_migration" in context.feature.tags and "windows" in context.feature.tags:
            name = "windows-vm-without-startup"

        elif "hot_migration" in context.feature.tags and "linux" in context.feature.tags:
            name = "linux-vm-with-startup"

        elif "hot_migration" in context.feature.tags and "windows" in context.feature.tags:
            name = "windows-vm-with-startup"

        fixture = helper.get_fixture(entity_singular)[name][entity_singular]
        label = fixture["label"]
        data = context.cp.search(entity_plural, args=label)

        if data:
            id = data[0][entity_singular]["id"]

            # check whether vm is in suspended state before delete
            if data[0][entity_singular]["suspended"]:
                # activate it back by sending 'suspend' action again
                suspension_response = context.cp.post_action(entity_plural, id, "suspend")

                if suspension_response.status_code != 201:
                    assert False, "error: unable to activate the VM (%s) in onapp cloud" % label

            print("VM found in Onapp cloud, proceed to delete...")

            response = {}
            response[entity_plural] = context.cp.delete(entity_plural, id)

            sleep(60)

            if response[entity_plural].status_code == 204:
                print("VM has been deleted successfully")
            else:
                print("error: failed to delete, {error}".format(error=response[entity_plural].text))

        else:
            print("VM is not found, proceed to delete the VM in VHI portal")

        # VHI portal
        hostname = fixture["hostname"]
        config = helper.get_config()
        output = helper.open_vhi_ssh_connection(config["vhi"], "service compute server list -f json")
        vm_list = json.loads(output.stdout)

        match = False
        for vm in vm_list:

            if hostname in vm["name"]:
                match = True

                print("VM found in VHI portal, proceed to delete...")
                _ = helper.open_vhi_ssh_connection(config["vhi"], "service compute server delete {vm_name}".format(vm_name=vm["name"]))
                sleep(30)

                print("VM has been deleted successfully")
                break
        
        # we proceed with the rest of the scenario even if the vm is not found
        if not match:
            print("VM is not found in VHI portal, proceed to next scenario")