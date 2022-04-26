import collections
import shlex,subprocess
import os
import sys
import json
from collections import defaultdict

plug_path=os.getcwd()
sys.path.append(plug_path)
sys.path.append(plug_path+'inc')

from o2v_config import *
from functions import *
from onapp_helpers import *

 ######################
##-----FUNCTION-------##
##---list_onapp_vms---##
 ######################
def list_onapp_vms(vals='',by='',url=''):

    URL = ONAPP_CP_URL + '/virtual_machines.json'

    if vals == "" and by == "":
       jqexp = "jq -c '.[] | [ .virtual_machine.id , .virtual_machine.identifier , .virtual_machine.hostname , .virtual_machine.booted ]'"
    elif vals == "" and by != "":
       by_arg=by.split("=")[0]
       by_val=by.split("=")[1]
       jqexp = "jq -c '.[] | select(.virtual_machine.{by_a}=={by_v}) | [ .virtual_machine.id , .virtual_machine.identifier , .virtual_machine.hostname , .virtual_machine.booted ]'".format(by_a=by_arg,by_v=by_val)
    elif vals != "" and by != "":
       by_arg=by.split("=")[0]
       by_val=by.split("=")[1]
       vals_list = [ ".virtual_machine.{}".format(x) for x in vals.split(",") ]
       if len(vals_list) == 1:
          vals_list = vals_list[0]
       vals_str = str( vals_list ).replace("'",'')
       jqexp = "jq -c '.[] | select(.virtual_machine.{by_a}=={by_v}) | {vls} '".format(by_a=by_arg,by_v=by_val,vls=vals_str)
    else:
       vals_list = [ ".virtual_machine.{}".format(x) for x in vals.split(",") ]
       if len(vals_list) == 1:
          vals_list = vals_list[0]
       vals_str = str( vals_list ).replace("'",'')
       jqexp = "jq -c '.[] | {vls}'".format(vls=vals_str)

    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {res_url}".format(user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, res_url=URL) + " | {jqex}".format(jqex=jqexp)
    print ('-----')
    (rc,ou) = run_command(CMD,7,0)
    print ('---')
    print ("{}".format(ou))

    return (rc,ou.decode('ascii'))


 ######################
##----- FUNCTION ------##
##-get_onapp_vm_nics---##
 ######################
def get_onapp_vm_nics(vm_idn='',verbosity=8):

    VM_IDn = vm_idn

    #--OnApp: get source VM NICs' MACs info --#

    print('-------')
    print("-- OnApp: get VM's MACS --")
    URL = ONAPP_CP_URL + "/virtual_machines/{}/network_interfaces.json".format(VM_IDn)
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | [ .network_interface[\"id\"],.network_interface[\"mac_address\"],.network_interface[\"primary\"] ] '".format(user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL )
    (rc,ou) = run_command(CMD,8,0)
    API_VM_MACS = []
    for line in ou.splitlines():
       nic = json.loads(line)
       API_VM_MACS.append( { 'id': nic[0], 'mac': nic[1].encode('ascii'),'primary': nic[2] } ) 

    print('-------')
    print("-- OnApp: get VM's IP addresses --")
    URL = ONAPP_CP_URL + "/virtual_machines/{}/ip_addresses.json".format(VM_IDn)
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | [ .ip_address_join[\"network_interface_id\"],.ip_address_join[\"ip_address\"][\"address\"] ] '".format(user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL )
    (rc,ou) = run_command(CMD,8,0)
    API_VM_IPS = defaultdict( lambda: [] )
    for line in ou.splitlines():
       nic = json.loads(line)
       if nic[0] in API_VM_IPS.keys() : 
            API_VM_IPS[ nic[0] ].append( nic[1].encode('ascii') ) 
       else:
           API_VM_IPS[ nic[0] ] = [ nic[1].encode('ascii') ] 

    API_VM_NICS = []

    for idx,mac in enumerate(API_VM_MACS):
        nic_id = API_VM_MACS[idx]['id']
        API_VM_NICS.append( { 'id': nic_id, 'number': idx , 'mac': API_VM_MACS[idx]['mac'], 'ips': API_VM_IPS[nic_id],'primary': API_VM_MACS[idx]['primary'] } )

    return API_VM_NICS


 ##########################
##------- FUNCTION -------##
##---get_onapp_vm_disks---##
 ##########################
def get_onapp_vm_disks(vm_idn='',verbosity=8):

    VM_IDn = vm_idn

#--OnApp: get source VM data_stores --#
    print('-------')
    print("-- OnApp: get OnApp datastores --")
    URL = ONAPP_CP_URL + "/settings/data_stores.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | [ .data_store.id , .data_store.identifier ] '".format(user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL)
    (rc,ou) = run_command(CMD,7,0)
    API_DS = {}
    for line in ou.splitlines():
       ds = json.loads(line)
       API_DS[ ds[0] ] = ds[1].encode('ascii')
    print ("ONAPP_DATASTORES: \n" + str(API_DS))
    print("")

#--OnApp: get source VM disks --#
    print('-------')
    print("-- OnApp: get VM's disks by {identifier} --")
    URL = ONAPP_CP_URL + "/virtual_machines/{}/disks.json".format(VM_IDn)
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | [ .disk.identifier,.disk.data_store_id,.disk.disk_size,.disk.disk_vm_number,.disk.primary,.disk.is_swap ] '".format(user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL )
    (rc,ou) = run_command(CMD,8,0)
    API_VM_DISKS = []
    for line in ou.splitlines():
       dsk = json.loads(line)
       API_VM_DISKS.append( { 'disk_idn': dsk[0].encode('ascii'),'ds_id':dsk[1], 'size': dsk[2], 'number': dsk[3], 'primary': dsk[4], "is_swap": dsk[5],'path': "/dev/"+str(API_DS[dsk[1]])+"/"+str(dsk[0]),'datastore_idn': str(API_DS[dsk[1]]) } )

    return API_VM_DISKS



 ##########################
##------- FUNCTION -------##
##---get_onapp_vm_primary_disk---##
 ##########################
def get_onapp_vm_primary_disk(vm_idn='',verbosity=8):

    VM_IDn = vm_idn

#--OnApp: get source VM data_stores --#
    print('-------')
    print("-- OnApp: get OnApp datastores --")
    URL = ONAPP_CP_URL + "/settings/data_stores.json"
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | [ .data_store.id , .data_store.identifier ] '".format(user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL)
    (rc,ou) = run_command(CMD,7,0)
    API_DS = {}
    for line in ou.splitlines():
       ds = json.loads(line)
       API_DS[ ds[0] ] = ds[1].encode('ascii')
    print ("ONAPP_DATASTORES: \n" + str(API_DS))
    print("")

#--OnApp: get source VM disks --#
    print('-------')
    print("-- OnApp: get VM's disks by {identifier} --")
    URL = ONAPP_CP_URL + "/virtual_machines/{}/disks.json".format(VM_IDn)
    CMD = "curl -k -s -X GET -H 'Accept: application/json' -H 'Content-type: application/json' -u {user_email}:{user_apikey} {full_url} | jq -c '.[] | select(.disk.primary==true) | [ .disk.identifier,.disk.data_store_id ] '".format(user_email=ONAPP_USER_EMAIL, user_apikey=ONAPP_USER_APIKEY, full_url=URL )
    (rc,ou) = run_command(CMD,8,0)
    API_VM_PRIMARY_DISK = []
    for line in ou.splitlines():
       dsk = json.loads(line)
       API_VM_PRIMARY_DISK.append( { 'path': "/dev/"+str(API_DS[dsk[1]])+"/"+str(dsk[0]) } )

    return API_VM_PRIMARY_DISK
