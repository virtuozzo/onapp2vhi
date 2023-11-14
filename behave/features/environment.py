from fixtures.helper import helper
from time import sleep
import json

def before_all(context):

    context.entity_to_delete = {}

def before_scenario(context, scenario):

    if "network" in scenario.tags:
        context.arr_network_to_delete = []
        
def after_scenario(context, scenario):
    
    if "migrate_vm" in context.feature.tags:
        
        # onapp cloud
        entity_plural = "virtual_machines"
        entity_singular = "virtual_machine"

        if "cold_migration" in context.feature.tags and "linux" in context.feature.tags and "statichv" in context.feature.tags:
            name = "linux-vm-without-startup-static"

        elif "cold_migration" in context.feature.tags and "windows" in context.feature.tags and "statichv" in context.feature.tags:
            name = "windows-vm-without-startup-static"

        elif "hot_migration" in context.feature.tags and "linux" in context.feature.tags and "statichv" in context.feature.tags:
            name = "linux-vm-with-startup-static"

        elif "hot_migration" in context.feature.tags and "windows" in context.feature.tags and "statichv" in context.feature.tags:
            name = "windows-vm-with-startup-static"

        elif "cold_migration" in context.feature.tags and "linux" in context.feature.tags and "cloudboothv" in context.feature.tags:
            name = "linux-vm-without-startup-cloudboot"

        elif "cold_migration" in context.feature.tags and "windows" in context.feature.tags and "cloudboothv" in context.feature.tags:
            name = "windows-vm-without-startup-cloudboot"

        elif "hot_migration" in context.feature.tags and "linux" in context.feature.tags and "cloudboothv" in context.feature.tags:
            name = "linux-vm-with-startup-cloudboot"

        elif "hot_migration" in context.feature.tags and "windows" in context.feature.tags and "cloudboothv" in context.feature.tags:
            name = "windows-vm-with-startup-cloudboot"

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

                # find the volume from server
                volume_output = helper.open_vhi_ssh_connection(config["vhi"], "service compute server volume list --server %s -f json" % vm["name"])
                arr_volume = json.loads(volume_output.stdout)

                arr_device = []
                for device in arr_volume:
                    arr_device.append(device["id"])
                
                # to delete vm in vhi portal
                print("VM found in VHI portal, proceed to delete...")
                _ = helper.open_vhi_ssh_connection(config["vhi"], "service compute server delete {vm_name}".format(vm_name=vm["name"]))

                print("VM has been deleted successfully")
                break
        
        # we proceed with the rest of the scenario even if the vm is not found
        if not match:
            print("VM is not found in VHI portal, proceed to next scenario")
        
        if "arr_device" in locals():
            for id in arr_device:
                try:
                    # delete volume, ignore if there's none to delete
                    _ = helper.open_vhi_ssh_connection(config["vhi"], "service compute volume delete %s" % id)
                    print("volume %s has been removed" % id)
                except:
                    pass
                
        # only delete the storage policy that we created using behave
        if context.entity_to_delete.get("storage_policy"):
            storage_policy = context.entity_to_delete["storage_policy"]["name"]
            _ = helper.open_vhi_ssh_connection(config["vhi"], "service compute storage-policy delete %s" % storage_policy)
            print("storage policy named %s has been removed" % storage_policy)

        if context.entity_to_delete.get("placement"):
            arr_node = context.entity_to_delete["placement"]["nodes"].split(",")
            name = context.entity_to_delete["placement"]["name"]

            for node in arr_node:
                _ = helper.open_vhi_ssh_connection(config["vhi"], "service compute placement delete-assign --node {node} {name}"\
                                                    .format(node=node, name=name))
                print("node named %s has been unassigned from placement %s" % (node, name))

            # to unassign flavour from placement
            placement_output = helper.open_vhi_ssh_connection(config["vhi"], "service compute placement show %s -f json" % name)
            placement_id = json.loads(placement_output.stdout)["id"]
            
            flavor_placement_output = helper.open_vhi_ssh_connection(config["vhi"], "service compute flavor list --long -c name -c placements -f json")
            flavor_placement = json.loads(flavor_placement_output.stdout)

            match = False
            for flavor in flavor_placement:
                for placement in flavor["placements"]:
                    if placement == placement_id:
                        flavor_name = flavor["name"]
                        match = True
                        break

            if not match:
                assert False, "error: flavor is not found in placement"
            
            _ = helper.open_vhi_ssh_connection(config["vhi"], "service compute placement delete-assign --flavor {flavor} {name}"\
                                                    .format(flavor=flavor_name, name=name))
            print("flavor named %s has been unassigned from placement %s" % (flavor_name, name))

            _ = helper.open_vhi_ssh_connection(config["vhi"], "service compute placement delete {name}".format(name=name))
            print("placement named %s has been removed" % name)

        if "network" in context.scenario.tags:
            
            for network in context.entity_to_delete["network"]:

                _ = helper.open_vhi_ssh_connection(config["vhi"], "service compute network delete %s" % "network_" + network)
                print("network named {network_name} has been removed".format(network_name="network_" + network))
