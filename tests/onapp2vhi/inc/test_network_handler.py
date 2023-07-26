from unittest import TestCase
from mock import patch, mock_open, Mock

from onapp2vhi.inc.network_handler import get_network_configuration
from onapp2vhi.utilities.config import OnApp2VHIConfig
from onapp2vhi.inc.rest_client import OnAppRequests
from onapp2vhi.inc.ssh_connector import SSH


TEST_CONFIG = """
[onapp]
host = dummy.onappdev.com
url = http://dummy.onappdev.com
api_key = dummy_api_key
email = unittest@virtuozzo.com
cp_ssh_port = 2222
hv_ssh_port = 22

[vhi]
url = https://vhi.onappdev.com:8888
panel_url = https://vhi-panel.onappdev.com:8800
api_path = /api/v2
login = admin
admin_ui_pwd = ui_admin_password
hv_ip = 10.63.0.64
cp_ip = 10.63.0.63
network = public2
cloud_ssh_port = 2222
hv_ssh_port = 22
linux_image = debian-10-openstack-amd64.qcow2
windows_image = windows2012
domain_id = 58fa18b2cefc4bad8a52f11008dfbf72
vinfra_domain = Migration
vinfra_project = migproj
vinfra_user = user_login
vinfra_pass = user_pwd
vinfra_domain_user = ''
vinfra_domain_pass = ''

 Network ID for migration VM's, you can get it on VHI cloud
migration_network_id = 5afcb27b-1c92-4561-a81c-fcf4f89bd543

[key]
ssh_key = path/to/your/ssh_key/id_rsa
"""


class GetNetworkConfigurationTestCase(TestCase):

    @patch("builtins.open", mock_open(read_data=TEST_CONFIG))
    def setUp(self):
        self.mock_cfg = OnApp2VHIConfig.load_config('test.ini')
        self.mock_onapprequests = Mock(spec=OnAppRequests)
        self.mock_ssh = Mock(spec=SSH)

    @patch('onapp2vhi.inc.network_vhi.SSH')
    @patch('onapp2vhi.inc.network_onapp.OnAppRequests')
    @patch('onapp2vhi.inc.onapp_helpers.OnAppRequests')
    def test_get_configuration_ok(self, mock_onapprequests1, mock_onapprequests2, mock_ssh):

        def mock_onapprequests_get(param:str):
            if param == 'version':
                return { 'version': '6.4.3-unittest' }
            elif param == 'virtual_machines/abcdef':
                return {
                    'virtual_machine': {
                        'id': 12,
                        'identifier': 'abcdef',
                        'hypervisor_id': 6,
                    }
                }
            elif param == 'virtual_machines/abcdef/network_interfaces':
                return [
                    {
                        'network_interface': {
                            'id': 879,
                            'mac_address': '00:16:3e:11:05:1d',
                            'network_join_id': 2,
                            'primary': True,
                        }
                    },
                    {
                        'network_interface': {
                            'id': 880,
                            'mac_address': '00:16:3e:3f:20:27',
                            'network_join_id': 10,
                            'primary': None,
                        }
                    }
                ]

            elif param == 'virtual_machines/abcdef/ip_addresses':
                return [
                    {
                        'ip_address_join': {
                            'ip_address': {
                                'address': '10.119.0.7',
                                'ip_net_id': 2,
                                'ip_range_id': 2,
                                'ipv4': True,
                                'primary': True,
                            },
                            'network_interface_id': 879,
                        }
                    },
                    {
                        'ip_address_join': {
                            'ip_address': {
                                'address': '2a01:a240:a240::2',
                                'ip_net_id': 6,
                                'ip_range_id': 7,
                                'ipv4': False,
                                'primary': False,
                            },
                            'network_interface_id': 879,
                        }
                    },
                    {
                        'ip_address_join': {
                            'id': 1001,
                            'ip_address': {
                                'address': '2a01:a240:a240::102',
                                'ip_net_id': 15,
                                'ip_range_id': 18,
                                'ipv4': False,
                                'primary': False,
                            },
                            'network_interface_id': 880,
                        }
                    },
                    {
                        'ip_address_join': {
                            'id': 999,
                            'ip_address': {
                                'address': '192.168.17.2',
                                'ip_net_id': 12,
                                'ip_range_id': 15,
                                'ipv4': True,
                                'primary': True,
                            },
                            'network_interface_id': 880,
                        }
                    }
                ]
            elif param == 'settings/hypervisors/6':
                return {
                    'hypervisor': {
                        'hypervisor_group_id': 4,
                        'id': 6,
                    }
                }
            elif param == 'settings/hypervisors/6/network_joins':
                return []
            elif param == 'settings/hypervisor_zones/4/network_joins':
                return [
                    {
                        'network_join': {
                            'id': 2,
                            'identifier': 'itppqegtusuuxd-2',
                        }
                    },
                    {
                        'network_join': {
                            'id': 6,
                            'identifier': 'tsnmdzxxnglnfk-6',
                        }
                    },
                    {
                        'network_join': {
                            'id': 10,
                            'identifier': 'kshlwiyxjzwuyz-10',
                        }
                    },
                    {
                        'network_join': {
                            'id': 16,
                            'identifier': 'fphnsxldatvvop-16',
                        }
                    }
                ]
            elif param == 'settings/networks':
                return [
                    {
                        'network': {
                            'id': 2,
                            'identifier': 'itppqegtusuuxd',
                        }
                    },
                    {
                        'network': {
                            'id': 3,
                            'identifier': 'kshlwiyxjzwuyz',
                        }
                    },
                ]
            elif param == 'settings/nameservers':
                return [
                    {
                        'nameserver': {
                            'address': '8.8.8.8',
                            'network_id': 2,
                        }
                    },
                    {
                        'nameserver': {
                            'address': '2001:4860:4860::8888',
                            'network_id': 3,
                        }
                    },
                    {
                        'nameserver': {
                            'address': '2001:4860:4860::8888',
                            'network_id': 2,
                        }
                    }
                ]
            elif param == 'settings/networks/2/ip_nets/2':
                return {
                    'ip_net': {
                        'network_address': '10.119.0.0',
                        'network_mask': 24,
                    }
                }
            elif param == 'settings/networks/2/ip_nets/2/ip_ranges/2':
                return {
                    'ip_range': {
                        'default_gateway': '10.119.0.1',
                        'end_address': '10.119.0.254',
                        'start_address': '10.119.0.3',
                    }
                }
            elif param == 'settings/networks/3/ip_nets/15':
                return {
                    'ip_net': {
                        'network_address': '192.168.17.0',
                        'network_mask': 24,
                    }
                }
            elif param == 'settings/networks/3/ip_nets/15/ip_ranges/18':
                return {
                    'ip_range': {
                        'default_gateway': '192.168.17.1',
                        'end_address': '192.168.17.20',
                        'start_address': '192.168.17.2',
                    }
                }

            raise RuntimeError(f'unhandled path = {param}')

        self.mock_onapprequests.get.side_effect = mock_onapprequests_get

        def mock_ssh_execute(cmd:str):
            if 'service compute network list' in cmd:
                return (0, '''
[
  {
    "subnet": {
      "enable_dhcp": false, 
      "network_id": "071ca5da-78e2-4fa4-b15e-e7d4c676c3a4", 
      "dns_nameservers": [], 
      "ipv6_ra_mode": null, 
      "allocation_pools": [
        {
          "start": "172.16.9.2", 
          "end": "172.16.9.254"
        }
      ], 
      "gateway_ip": "172.16.9.1", 
      "ip_version": 4, 
      "ipv6_address_mode": null, 
      "cidr": "172.16.9.0/24", 
      "id": "0d9793cf-9f5e-4141-b104-d436177d24d3"
    }, 
    "id": "071ca5da-78e2-4fa4-b15e-e7d4c676c3a4", 
    "subnets": [
      {
        "enable_dhcp": false, 
        "network_id": "071ca5da-78e2-4fa4-b15e-e7d4c676c3a4", 
        "dns_nameservers": [], 
        "ipv6_ra_mode": null, 
        "allocation_pools": [
          {
            "start": "172.16.9.2", 
            "end": "172.16.9.254"
          }
        ], 
        "gateway_ip": "172.16.9.1", 
        "ip_version": 4, 
        "ipv6_address_mode": null, 
        "cidr": "172.16.9.0/24", 
        "id": "0d9793cf-9f5e-4141-b104-d436177d24d3"
      }, 
      {
        "enable_dhcp": false, 
        "network_id": "071ca5da-78e2-4fa4-b15e-e7d4c676c3a4", 
        "dns_nameservers": [], 
        "ipv6_ra_mode": null, 
        "allocation_pools": [
          {
            "start": "2a01:a240:a240::204", 
            "end": "2a01:a240:a240::2fe"
          }
        ], 
        "gateway_ip": "2a01:a240:a240::203", 
        "ip_version": 6, 
        "ipv6_address_mode": null, 
        "cidr": "2a01:a240:a240::200/120", 
        "id": "9449b97d-4008-4e3a-acd7-c66a19a0554b"
      }
    ], 
    "name": "tpp", 
    "ip_version": 4
  }, 
  {
    "subnet": {
      "enable_dhcp": false, 
      "network_id": "271f403b-0222-4257-8e36-9c6a04857369", 
      "dns_nameservers": [], 
      "ipv6_ra_mode": null, 
      "allocation_pools": [
        {
          "start": "10.119.0.3", 
          "end": "10.119.0.254"
        }
      ], 
      "gateway_ip": "10.119.0.1", 
      "ip_version": 4, 
      "ipv6_address_mode": null, 
      "cidr": "10.119.0.0/24", 
      "id": "e632699a-c783-4812-8aab-90a6f028ebb5"
    }, 
    "id": "271f403b-0222-4257-8e36-9c6a04857369", 
    "subnets": [
      {
        "enable_dhcp": false, 
        "network_id": "271f403b-0222-4257-8e36-9c6a04857369", 
        "dns_nameservers": [], 
        "ipv6_ra_mode": null, 
        "allocation_pools": [
          {
            "start": "10.119.0.3", 
            "end": "10.119.0.254"
          }
        ], 
        "gateway_ip": "10.119.0.1", 
        "ip_version": 4, 
        "ipv6_address_mode": null, 
        "cidr": "10.119.0.0/24", 
        "id": "e632699a-c783-4812-8aab-90a6f028ebb5"
      }, 
      {
        "enable_dhcp": false, 
        "network_id": "271f403b-0222-4257-8e36-9c6a04857369", 
        "dns_nameservers": [], 
        "ipv6_ra_mode": null, 
        "allocation_pools": [
          {
            "start": "2a01:a240:a240::2", 
            "end": "2a01:a240:a240::fe"
          }
        ], 
        "gateway_ip": "2a01:a240:a240::1", 
        "ip_version": 6, 
        "ipv6_address_mode": null, 
        "cidr": "2a01:a240:a240::/120", 
        "id": "5cfffb2f-cf0d-4eb1-8d32-35b08630dd35"
      }
    ], 
    "name": "network_itppqegtusuuxd", 
    "ip_version": 4
  }, 
  {
    "subnet": {
      "enable_dhcp": true, 
      "network_id": "522afdcc-56a5-4b7c-9f5f-034875a4db00", 
      "dns_nameservers": [
        "0.0.0.0"
      ], 
      "ipv6_ra_mode": null, 
      "allocation_pools": [
        {
          "start": "192.168.128.1", 
          "end": "192.168.128.254"
        }
      ], 
      "gateway_ip": null, 
      "ip_version": 4, 
      "ipv6_address_mode": null, 
      "cidr": "192.168.128.0/24", 
      "id": "7d042ece-5eef-4261-a6bd-6c1c8a23ffe0"
    }, 
    "id": "522afdcc-56a5-4b7c-9f5f-034875a4db00", 
    "subnets": [
      {
        "enable_dhcp": true, 
        "network_id": "522afdcc-56a5-4b7c-9f5f-034875a4db00", 
        "dns_nameservers": [
          "0.0.0.0"
        ], 
        "ipv6_ra_mode": null, 
        "allocation_pools": [
          {
            "start": "192.168.128.1", 
            "end": "192.168.128.254"
          }
        ], 
        "gateway_ip": null, 
        "ip_version": 4, 
        "ipv6_address_mode": null, 
        "cidr": "192.168.128.0/24", 
        "id": "7d042ece-5eef-4261-a6bd-6c1c8a23ffe0"
      }
    ], 
    "name": "private", 
    "ip_version": 4
  }, 
  {
    "subnet": {
      "enable_dhcp": false, 
      "network_id": "6a152778-cd18-4444-a444-b3513d32128d", 
      "dns_nameservers": [], 
      "ipv6_ra_mode": null, 
      "allocation_pools": [
        {
          "start": "192.168.17.2", 
          "end": "192.168.17.20"
        }
      ], 
      "gateway_ip": "192.168.17.1", 
      "ip_version": 4, 
      "ipv6_address_mode": null, 
      "cidr": "192.168.17.0/24", 
      "id": "6e8a6d76-14ed-47b0-b2c1-2a2e430ed40c"
    }, 
    "id": "6a152778-cd18-4444-a444-b3513d32128d", 
    "subnets": [
      {
        "enable_dhcp": true, 
        "network_id": "6a152778-cd18-4444-a444-b3513d32128d", 
        "dns_nameservers": [], 
        "ipv6_ra_mode": null, 
        "allocation_pools": [
          {
            "start": "2a01:a240:a240::102", 
            "end": "2a01:a240:a240::1fe"
          }
        ], 
        "gateway_ip": "2a01:a240:a240::101", 
        "ip_version": 6, 
        "ipv6_address_mode": null, 
        "cidr": "2a01:a240:a240::100/120", 
        "id": "52537e33-9680-420c-ae4a-b5f190007bc8"
      }, 
      {
        "enable_dhcp": false, 
        "network_id": "6a152778-cd18-4444-a444-b3513d32128d", 
        "dns_nameservers": [], 
        "ipv6_ra_mode": null, 
        "allocation_pools": [
          {
            "start": "192.168.17.2", 
            "end": "192.168.17.20"
          }
        ], 
        "gateway_ip": "192.168.17.1", 
        "ip_version": 4, 
        "ipv6_address_mode": null, 
        "cidr": "192.168.17.0/24", 
        "id": "6e8a6d76-14ed-47b0-b2c1-2a2e430ed40c"
      }
    ], 
    "name": "network_kshlwiyxjzwuyz", 
    "ip_version": 4
  }
]
Next columns are deprecated: enable_dhcp, dns_nameservers, allocation_pools, gateway_ip, ip_version, cidr. Use subnets[] fields.
''')
            raise RuntimeError(f'unhandle cmd = {cmd}')

        self.mock_ssh.execute.side_effect = mock_ssh_execute

        mock_onapprequests1.return_value = self.mock_onapprequests
        mock_onapprequests2.return_value = self.mock_onapprequests
        mock_ssh.return_value = self.mock_ssh

        result = get_network_configuration(self.mock_cfg, 'abcdef', 'test-project')
        self.assertIn('id=271f403b-0222-4257-8e36-9c6a04857369', result)
        self.assertIn("fixed-ip='10.119.0.7'", result)
        self.assertIn("fixed-ip='2a01:a240:a240::2'", result)
        self.assertIn("mac='00:16:3e:11:05:1d'", result)
        self.assertIn('id=6a152778-cd18-4444-a444-b3513d32128d', result)
        self.assertIn("fixed-ip='2a01:a240:a240::102'", result)
        self.assertIn("fixed-ip='192.168.17.2'", result)
        self.assertIn("mac='00:16:3e:3f:20:27'", result)
