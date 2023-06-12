CONFIG_TEMPLATE = """#[onapp]
#host = 69.168.239.170
#url = http://69.168.239.170
#api_key = here_is_yours_admin_api_key
#email = your_mail@gmail.com
#cp_ssh_port = 2222
#hv_ssh_port = 22
#
#[vhi]
#url = https://cvhi.onappdev.com:8888
#panel_url = https://cvhi.onappdev.com:8800
#api_path = /api/v2
#login = admin
#admin_ui_pwd = ui_admin_password
#hv_ip = 10.63.0.64
#cp_ip = 10.63.0.63
#network = public2
#cloud_ssh_port = 2222
#hv_ssh_port = 22
#linux_image = debian-10-openstack-amd64.qcow2
#windows_image = windows2012
#domain_id = 58fa18b2cefc4bad8a52f11008dfbf72
#vinfra_domain = Migration
#vinfra_project = migproj
#vinfra_user = user_login
#vinfra_pass = user_pwd
#vinfra_domain_user = ''
#vinfra_domain_pass = ''
#
# Network ID for migration VM's, you can get it on VHI cloud
#migration_network_id = 5afcb27b-1c92-4561-a81c-fcf4f89bd543
#
#[key]
#ssh_key = path/to/your/ssh_key/id_rsa
"""
