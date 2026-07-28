import json
from unittest import TestCase
from mock import patch, mock_open

from onapp2vhi.ops.live_migrate import vm_live_migrate
from onapp2vhi.utilities.config import OnApp2VHIConfig


TEST_CONFIG = """
[onapp]
host = dummy.onapp.virtuozzo.com
url = http://dummy.onapp.virtuozzo.com
api_key = dummy_api_key
email = unittest@virtuozzo.com
cp_ssh_port = 2222
hv_ssh_port = 22

[vhi]
url = https://vhi.onapp.virtuozzo.com:8888
panel_url = https://vhi-panel.onapp.virtuozzo.com:8800
api_path = /api/v2
login = admin
admin_ui_pwd = ui_admin_password
hv_ip = 10.0.0.2
cp_ip = 127.0.0.1
cp_ip_internal = 192.168.1.11
network = public2
cloud_ssh_port = 2222
hv_ssh_port = 22
linux_image = debian-10-openstack-amd64.qcow2
windows_image = windows2012
domain_id = 00000000000000000000000000000000
vinfra_domain = Migration
vinfra_project = migproj
vinfra_user = user_login
vinfra_pass = user_pwd
vinfra_domain_user = ''
vinfra_domain_pass = ''

 Network ID for migration VM's, you can get it on VHI cloud
migration_network_id = 00000000-0000-0000-0000-000000000001

vhi_secondary_security_group = 1234-1234fasd-safce0-adsfew

[key]
ssh_key = path/to/your/ssh_key/id_rsa
"""


class TestLiveMigrate(TestCase):

    @patch("builtins.open", mock_open(read_data=TEST_CONFIG))
    def setUp(self):
        self.mock_cfg = OnApp2VHIConfig.load_config("test.ini")

    @patch("os.unlink")
    @patch("onapp2vhi.ops.live_migrate.KVMxml")
    @patch("onapp2vhi.ops.live_migrate.ssh_run")
    @patch("onapp2vhi.ops.live_migrate.VinfraCommand")
    @patch("onapp2vhi.ops.live_migrate.SSH")
    @patch("onapp2vhi.ops.live_migrate.suspend_vm")
    @patch("onapp2vhi.ops.live_migrate.get_vhi_hv_ip")
    @patch("onapp2vhi.ops.live_migrate.check_sg_exists_in_project")
    @patch("onapp2vhi.ops.live_migrate.attach_security_group_to_nic_and_enable_spoofing")
    @patch("onapp2vhi.ops.live_migrate.transfer_firewall_rules_to_sg")
    @patch("onapp2vhi.ops.live_migrate.get_iface_from_specific_vs")
    @patch("onapp2vhi.ops.live_migrate.create_new_vhi_vm")
    @patch("onapp2vhi.ops.live_migrate.select_vm_network_configuration")
    @patch("onapp2vhi.ops.live_migrate.get_onapp_vm_disks")
    @patch("onapp2vhi.ops.live_migrate.get_onapp_vm_nics")
    @patch("onapp2vhi.ops.live_migrate.get_onapp_vm_flavor")
    @patch("onapp2vhi.inc.vhi_helpers.Vhi")
    def test_migrate_ok(self,
                        mock_vhi,
                        mock_get_onapp_vm_flavor,
                        mock_get_onapp_vm_nics,
                        mock_get_onapp_vm_disks,
                        mock_select_vm_network_configuration,
                        mock_create_new_vhi_vm,
                        mock_get_iface_from_specific_vs,
                        mock_transfer_firewall_rules_to_sg,
                        mock_attach_security_group_to_nic_and_enable_spoofing,
                        mock_check_sg_exists_in_project,
                        mock_get_vhi_hv_ip,
                        mock_suspend_vm,
                        mock_ssh,
                        mock_vinfra_cmd,
                        mock_ssh_run,
                        mock_kvmxml,
                        mock_unlink):

        mock_vdom = "behave"
        mock_vproj = "Default_Project"
        mock_idn = "testidn"
        mock_properties = {
            'hv_ip': '10.116.0.32',
            'vm_os': 'linux',
            'vm_ip_addr': '10.119.0.4',
            'network_info': {860: ['10.119.0.4']},
            'hot_migrate': True,
            'hostname': 'faidhi2',
            'domain': 'localdomain',
            'storage_policy': 'default',
            'flavor': 'flavor_1_1'
        }

        mock_ssh.return_value.execute.side_effect = [
            # check vm running
            (0, ''),
            # dump xml
            (0, '/tmp/onapp-sodfaypsdofiy.xml'),
            # find volume id in cinder
            (0, 'asdfoiurapfd'),
            # dump xml again
            (0, '/tmp/vhi-sdfaposifsdi.xml'),
            # live migrate run
            (0, ''),
            # verify vm create
            (0, 'Id: 123\nState:    running\nCpu: 4\n'),
            # shutdown onapp vm
            (0, ''),
            # start precreated vhi vm
            (0, '')
        ]
        mock_vinfra_cmd.return_value.execute.side_effect = [
            # no vms in VHI
            json.dumps([]),
            # server volume list
            json.dumps([{
                'id': 'asdofiasf',
                'device': '/dev/xda1',
                'result': 'ok',
            }]),
        ]
        mock_ssh_run.side_effect = [
            (0, ''),    # copy onapp vm xml
            (0, ''),    # copy vhi vm xml
            (0, '')     # upload xml for migration
        ]

        result = vm_live_migrate(self.mock_cfg,
                                 22,
                                 mock_vdom,
                                 mock_vproj,
                                 mock_idn,
                                 mock_properties,
                                 mock_vhi)
        self.assertTrue(result)

    @patch("os.unlink")
    @patch("onapp2vhi.ops.live_migrate.KVMxml")
    @patch("onapp2vhi.ops.live_migrate.ssh_run")
    @patch("onapp2vhi.ops.live_migrate.VinfraCommand")
    @patch("onapp2vhi.ops.live_migrate.SSH")
    @patch("onapp2vhi.ops.live_migrate.suspend_vm")
    @patch("onapp2vhi.ops.live_migrate.get_vhi_hv_ip")
    @patch("onapp2vhi.ops.live_migrate.check_sg_exists_in_project")
    @patch("onapp2vhi.ops.live_migrate.attach_security_group_to_nic_and_enable_spoofing")
    @patch("onapp2vhi.ops.live_migrate.transfer_firewall_rules_to_sg")
    @patch("onapp2vhi.ops.live_migrate.get_iface_from_specific_vs")
    @patch("onapp2vhi.ops.live_migrate.create_new_vhi_vm")
    @patch("onapp2vhi.ops.live_migrate.select_vm_network_configuration")
    @patch("onapp2vhi.ops.live_migrate.get_onapp_vm_disks")
    @patch("onapp2vhi.ops.live_migrate.get_onapp_vm_nics")
    @patch("onapp2vhi.ops.live_migrate.get_onapp_vm_flavor")
    @patch("onapp2vhi.inc.vhi_helpers.Vhi")
    def test_migrate_ok_with_empty_network_on_vhi(self,
                                                  mock_vhi,
                                                  mock_get_onapp_vm_flavor,
                                                  mock_get_onapp_vm_nics,
                                                  mock_get_onapp_vm_disks,
                                                  mock_select_vm_network_configuration,
                                                  mock_create_new_vhi_vm,
                                                  mock_get_iface_from_specific_vs,
                                                  mock_transfer_firewall_rules_to_sg,
                                                  mock_attach_security_group_to_nic_and_enable_spoofing,
                                                  mock_check_sg_exists_in_project,
                                                  mock_get_vhi_hv_ip,
                                                  mock_suspend_vm,
                                                  mock_ssh,
                                                  mock_vinfra_cmd,
                                                  mock_ssh_run,
                                                  mock_kvmxml,
                                                  mock_unlink):

        mock_vdom = "behave"
        mock_vproj = "Default_Project"
        mock_idn = "testidn"
        mock_properties = {
            'hv_ip': '10.116.0.32',
            'vm_os': 'linux',
            'vm_ip_addr': '10.119.0.4',
            'network_info': {860: ['10.119.0.4']},
            'hot_migrate': True,
            'hostname': 'faidhi2',
            'domain': 'localdomain',
            'storage_policy': 'default',
            'flavor': 'flavor_1_1'
        }

        mock_ssh.return_value.execute.side_effect = [
            # check vm running
            (0, ''),
            # dump xml
            (0, '/tmp/onapp-sodfaypsdofiy.xml'),
            # find volume id in cinder
            (0, 'asdfoiurapfd'),
            # dump xml again
            (0, '/tmp/vhi-sdfaposifsdi.xml'),
            # live migrate run
            (0, ''),
            # verify vm create
            (0, 'Id: 123\nState:    running\nCpu: 4\n'),
            # shutdown onapp vm
            (0, ''),
            # start precreated vhi vm
            (0, '')
        ]
        mock_vinfra_cmd.return_value.execute.side_effect = [
            json.dumps([{
                'id': 'testidn',
                'networks': [],
                'name': 'test',
                'status': 'OK',
            }]),
            # server volume list
            json.dumps([{
                'id': 'asdofiasf',
                'device': '/dev/xda1',
                'result': 'ok',
            }]),
        ]
        mock_ssh_run.side_effect = [
            (0, ''),    # copy onapp vm xml
            (0, ''),    # copy vhi vm xml
            (0, '')     # upload xml for migration
        ]

        result = vm_live_migrate(self.mock_cfg,
                                 22,
                                 mock_vdom,
                                 mock_vproj,
                                 mock_idn,
                                 mock_properties,
                                 mock_vhi)
        self.assertTrue(result)
