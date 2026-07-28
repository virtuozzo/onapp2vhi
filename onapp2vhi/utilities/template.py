CONFIG_TEMPLATE = """[onapp]
host = 127.0.0.1
url = http://127.0.0.1
api_key = here_is_yours_admin_api_key
email = your_mail@gmail.com
cp_ssh_port = 2222
hv_ssh_port = 22

[vhi]
url = https://cvhi.onapp.virtuozzo.com:8888
panel_url = https://cvhi.onapp.virtuozzo.com:8800
api_path = /api/v2
login = admin
admin_ui_pwd = ui_admin_password
hv_ip = 10.0.0.2
cp_ip = 127.0.0.1
cp_ip_internal = 192.168.0.1
network = public2
cloud_ssh_port = 2222
hv_ssh_port = 22
linux_image = debian-10-openstack-amd64.qcow2
windows_image = windows2012
domain_id = 00000000000000000000000000000000
vinfra_domain = Migration
vinfra_project = migproj
vinfra_user = user_login
vhi_storage_policy = default
vinfra_pass = user_pwd
vinfra_domain_user = ''
vinfra_domain_pass = ''
remove_disk_on_termination = yes

# Network ID for migration VM's, you can get it on VHI cloud
migration_network_id = 00000000-0000-0000-0000-000000000001
# Security Group ID specified to use for 2nd, 3rd, ... NIC's
vhi_secondary_security_group = 00000000-0000-0000-0000-000000000002

[key]
ssh_key = path/to/your/ssh_key/id_rsa
"""
