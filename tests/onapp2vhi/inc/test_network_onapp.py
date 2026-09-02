from unittest import TestCase
from mock import patch, Mock


from onapp2vhi.inc.network_onapp import (
    NetworkInterface,
    NetworkInterfaces,
    get_virtual_server_hypervisor,
    get_virtual_server_interfaces,
    get_virtual_server_ip_addresses,
    get_hypervisor_group_id,
    get_hypervisor_network_join,
    get_hypervisor_group_network_join,
    get_network_nameserver,
    get_network_interfaces,
    get_network_id_by_identifier,
    get_ip_net,
    get_ip_range,
    nic_has_multiple_ips,
)
from onapp2vhi.inc.rest_client import OnAppRequests
from onapp2vhi.utilities.config import OnApp2VHIConfig


class NetworkInferfaceTestCase(TestCase):

    # TODO! add parameter checking

    def test_construct_no_param(self):
        network_interface = NetworkInterface()
        self.assertEqual(network_interface.virtual_server_id, "")
        self.assertEqual(network_interface.hypervisor_id, "")
        self.assertEqual(network_interface.network_join_identifier, "")
        self.assertEqual(network_interface.network_identifier, "")
        self.assertEqual(network_interface.ip_net, "")
        self.assertEqual(network_interface.ip_range, "")
        self.assertEqual(network_interface.network_nameserver, "")
        self.assertEqual(network_interface.ip_addresses, [])
        self.assertEqual(network_interface.ipv4, False)
        self.assertEqual(network_interface.primary, False)
        self.assertEqual(network_interface.mac_address, "")
        self.assertEqual(network_interface.label, "network_")

    def test_construct_wrong_param(self):
        network_interface = NetworkInterface(ipv6="abcd")
        self.assertEqual(network_interface.virtual_server_id, "")
        self.assertEqual(network_interface.hypervisor_id, "")
        self.assertEqual(network_interface.network_join_identifier, "")
        self.assertEqual(network_interface.network_identifier, "")
        self.assertEqual(network_interface.ip_net, "")
        self.assertEqual(network_interface.ip_range, "")
        self.assertEqual(network_interface.network_nameserver, "")
        self.assertEqual(network_interface.ip_addresses, [])
        self.assertEqual(network_interface.ipv4, False)
        self.assertEqual(network_interface.primary, False)
        self.assertEqual(network_interface.mac_address, "")
        self.assertEqual(network_interface.label, "network_")

    def test_construct_set_a_param(self):
        network_interface = NetworkInterface(virtual_server_id="abcd")
        self.assertEqual(network_interface.virtual_server_id, "abcd")

    def test_object_repr(self):
        network_interface = NetworkInterface(network_identifier="abcdef")
        self.assertEqual(repr(network_interface), "network_abcdef")


class NetworkInterfacesTestCase(TestCase):

    def setUp(self):
        self.network_interfaces = NetworkInterfaces()
        self.assertEqual(len(self.network_interfaces), 0)

    def test_add_network(self):
        self.network_interfaces.add(NetworkInterface(network_identifier="a"))
        self.assertEqual(len(self.network_interfaces), 1)

        self.network_interfaces.add(NetworkInterface(network_identifier="b"))
        self.assertEqual(len(self.network_interfaces), 2)

    def test_get_all(self):
        ni1 = NetworkInterface(network_identifier="a")
        ni2 = NetworkInterface(network_identifier="b")
        self.network_interfaces.add(ni1)
        self.network_interfaces.add(ni2)
        self.assertEqual(self.network_interfaces.get_all(), [ni1, ni2])

    @patch("onapp2vhi.inc.network_onapp.logs")
    def test_get_by_network_join(self, mock_logs):
        ni1 = NetworkInterface(network_identifier="a", network_join_identifier="1")
        ni2 = NetworkInterface(network_identifier="b", network_join_identifier="2")
        ni3 = NetworkInterface(network_identifier="c", network_join_identifier="1")
        self.network_interfaces.add(ni1)
        self.network_interfaces.add(ni2)
        self.network_interfaces.add(ni3)

        self.assertEqual(self.network_interfaces.get_by_network_join("1"), ni1)
        self.assertEqual(self.network_interfaces.get_by_network_join("2"), ni2)
        self.assertIsNone(self.network_interfaces.get_by_network_join("3"))


class BaseNetworkOnAppTestCase(TestCase):

    def setUp(self):
        self.mock_config = Mock(spec=OnApp2VHIConfig)
        self.mock_onapprequests = Mock(spec=OnAppRequests)


class GetVirtualServerHypervisorTestCase(BaseNetworkOnAppTestCase):

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_ok(self, mock_onapprequests_ctor):
        mock_response = {
            'virtual_machine': {
                'hypervisor_id': '1234',
            }
        }
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_virtual_server_hypervisor(self.mock_config, "abcd")

        self.mock_onapprequests.get.assert_called_with('virtual_machines/abcd')
        self.assertNotEqual(result, False)
        self.assertEqual(result, '1234')

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_failed(self, mock_onapprequests_ctor):
        mock_response = {}
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_virtual_server_hypervisor(self.mock_config, "abcd")

        self.mock_onapprequests.get.assert_called_with('virtual_machines/abcd')
        self.assertEqual(result, False)


class GetHypervisorGroupIdTestCase(BaseNetworkOnAppTestCase):

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_ok(self, mock_onapprequests_ctor):
        mock_response = {
            'hypervisor': {
                'hypervisor_group_id': 'abc'
            }
        }
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_hypervisor_group_id(self.mock_config, '123')
        self.mock_onapprequests.get.assert_called_with('settings/hypervisors/123')
        self.assertEqual(result, 'abc')

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_failed(self, mock_onapprequests_ctor):
        mock_response = {}
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_hypervisor_group_id(self.mock_config, '123')
        self.mock_onapprequests.get.assert_called_with('settings/hypervisors/123')
        self.assertEqual(result, '')


class GetHypervisorNetworkJoinTestCase(BaseNetworkOnAppTestCase):

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_ok(self, mock_onapprequests_ctor):
        mock_response = [
            {
                "network_join": {
                    "id": "b_network_join_id",
                    "identifier": "b_network_join_identifier"
                }
            }, {
                "network_join": {
                    "id": "a_network_join_id",
                    "identifier": "a_network_join_identifier"
                }
            }
        ]
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_hypervisor_network_join(self.mock_config, "a_hypervisor_id", "a_network_join_id")
        self.mock_onapprequests.get.assert_called_with('settings/hypervisors/a_hypervisor_id/network_joins')
        self.assertEqual(result, 'a_network_join_identifier')

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_failed(self, mock_onapprequests_ctor):
        mock_response = [
            {
                "network_join": {
                    "id": "b_network_join_id",
                    "identifier": "b_network_join_identifier"
                }
            },
        ]
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_hypervisor_network_join(self.mock_config, "a_hypervisor_id", "a_network_join_id")
        self.mock_onapprequests.get.assert_called_with('settings/hypervisors/a_hypervisor_id/network_joins')
        self.assertEqual(result, '')


class GetHypervisorGroupNetworkJoinTestCase(BaseNetworkOnAppTestCase):

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_ok(self, mock_onapprequests_ctor):
        mock_response = [
            {
                "network_join": {
                    "id": "b_network_join_id",
                    "identifier": "b_network_join_identifier"
                }
            }, {
                "network_join": {
                    "id": "a_network_join_id",
                    "identifier": "a_network_join_identifier"
                }
            }
        ]
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_hypervisor_group_network_join(self.mock_config, "a_hypervisor_group_id", "a_network_join_id")
        self.mock_onapprequests.get.assert_called_with('settings/hypervisor_zones/a_hypervisor_group_id/network_joins')
        self.assertEqual(result, 'a_network_join_identifier')

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_failed(self, mock_onapprequests_ctor):
        mock_response = [
            {
                "network_join": {
                    "id": "b_network_join_id",
                    "identifier": "b_network_join_identifier"
                }
            }
        ]
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_hypervisor_group_network_join(self.mock_config, "a_hypervisor_group_id", "a_network_join_id")
        self.mock_onapprequests.get.assert_called_with('settings/hypervisor_zones/a_hypervisor_group_id/network_joins')
        self.assertEqual(result, False)


class GetVirtualServerInterfaceTestCase(BaseNetworkOnAppTestCase):

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_ok(self, mock_onapprequests_ctor):
        mock_response = ["1.1.1.1"]
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_virtual_server_interfaces(self.mock_config, "asdf")
        self.mock_onapprequests.get.assert_called_with('virtual_machines/asdf/network_interfaces')
        self.assertEqual(result, ["1.1.1.1"])

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_failed(self, mock_onapprequests_ctor):
        mock_response = None
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_virtual_server_interfaces(self.mock_config, "asdf")
        self.mock_onapprequests.get.assert_called_with('virtual_machines/asdf/network_interfaces')
        self.assertEqual(result, [])


class GetVirtualServerIpAddressesTestCase(BaseNetworkOnAppTestCase):

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_ok(self, mock_onapprequests_ctor):
        mock_response = [
            {
                "ip_address_join": {
                    "network_interface_id": "a_network_interface_id",
                    "ip_address": "127.0.0.1",
                },
            },
        ]
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_virtual_server_ip_addresses(self.mock_config,
                                                 "a_server_id",
                                                 "a_network_interface_id")

        self.mock_onapprequests.get.assert_called_with('virtual_machines/a_server_id/ip_addresses')
        self.assertEqual(result, ['127.0.0.1'])

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_failed(self, mock_onapprequests_ctor):
        mock_response = []
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_virtual_server_ip_addresses(self.mock_config,
                                                 "a_server_id",
                                                 "a_network_interface_id")

        self.mock_onapprequests.get.assert_called_with('virtual_machines/a_server_id/ip_addresses')
        self.assertEqual(result, [])


class GetNetworkNameserverTestCase(BaseNetworkOnAppTestCase):

    @patch("onapp2vhi.inc.network_onapp.logs")
    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_ok_ipv4(self, mock_onapprequests_ctor, mock_logs):
        mock_response = [
            {
                "nameserver": {
                    "network_id": 1234,
                    "address": "8.8.4.4",
                }
            },
        ]
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_network_nameserver(self.mock_config,
                                        "1234",
                                        ipv4=True)

        self.mock_onapprequests.get.assert_called_with('settings/nameservers')
        mock_logs.info.assert_called_with(msg='Found resolver for IPv4 [8.8.4.4]')
        self.assertEqual(result, '8.8.4.4')

    @patch("onapp2vhi.inc.network_onapp.logs")
    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_ok_ipv6(self, mock_onapprequests_ctor, mock_logs):
        mock_response = [
            {
                "nameserver": {
                    "network_id": 1234,
                    "address": "F8:00:01",
                }
            },
        ]
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_network_nameserver(self.mock_config,
                                        "1234",
                                        ipv4=False)

        self.mock_onapprequests.get.assert_called_with('settings/nameservers')
        mock_logs.info.assert_called_with(msg='Found resolver for IPv6 [F8:00:01]')
        self.assertEqual(result, 'F8:00:01')

    @patch("onapp2vhi.inc.network_onapp.logs")
    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_failed(self, mock_onapprequests_ctor, mock_logs):
        mock_response = []
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_network_nameserver(self.mock_config,
                                        "a_network_id",
                                        ipv4=True)

        self.mock_onapprequests.get.assert_called_with('settings/nameservers')
        mock_logs.warn.assert_called_with(
            msg='Resolver not found for Network ID [a_network_id] IPv4: True')
        self.assertEqual(result, '')


class GetNetworkInterfaceTestCase(BaseNetworkOnAppTestCase):

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_ok(self, mock_onapprequests_ctor):
        mock_response = [{"some_key": "some_value"}]
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_network_interfaces(self.mock_config, "a_server_id")

        self.mock_onapprequests.get.assert_called_with('virtual_machines/a_server_id/network_interfaces')
        self.assertEqual(result, [{"some_key": "some_value"}])

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_failed(self, mock_onapprequests_ctor):
        mock_response = []
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_network_interfaces(self.mock_config, "a_server_id")

        self.mock_onapprequests.get.assert_called_with('virtual_machines/a_server_id/network_interfaces')
        self.assertFalse(result)


class GetIpNetTestCase(BaseNetworkOnAppTestCase):

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_ok(self, mock_onapprequests_ctor):
        mock_response = [{"some_key": "some_value"}]
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_ip_net(self.mock_config, "a_network_id", "an_ip_net_id")

        self.mock_onapprequests.get.assert_called_with(
            'settings/networks/a_network_id/ip_nets/an_ip_net_id')
        self.assertEqual(result, [{"some_key": "some_value"}])

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_failed(self, mock_onapprequests_ctor):
        mock_response = []
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_ip_net(self.mock_config, "a_network_id", "an_ip_net_id")

        self.mock_onapprequests.get.assert_called_with(
            'settings/networks/a_network_id/ip_nets/an_ip_net_id')
        self.assertFalse(result)


class GetIpRangeTestCase(BaseNetworkOnAppTestCase):

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_ok(self, mock_onapprequests_ctor):
        mock_response = [{"some_key": "some_value"}]
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_ip_range(self.mock_config, "a_network_id", "an_ip_net_id", "an_ip_range_id")

        self.mock_onapprequests.get.assert_called_with(
            'settings/networks/a_network_id/ip_nets/an_ip_net_id/ip_ranges/an_ip_range_id')
        self.assertEqual(result, [{"some_key": "some_value"}])

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_failed(self, mock_onapprequests_ctor):
        mock_response = []
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_ip_range(self.mock_config, "a_network_id", "an_ip_net_id", "an_ip_range_id")

        self.mock_onapprequests.get.assert_called_with(
            'settings/networks/a_network_id/ip_nets/an_ip_net_id/ip_ranges/an_ip_range_id')
        self.assertFalse(result)


class GetNetworkIdByIdentifier(BaseNetworkOnAppTestCase):

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_ok(self, mock_onapprequests_ctor):
        mock_response = [{
            "network": {
                "id": "an_id",
                "identifier": "a_network_identifier",
            }
        }]
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_network_id_by_identifier(self.mock_config, "a_network_identifier")

        self.mock_onapprequests.get.assert_called_with('settings/networks')
        self.assertEqual(result, 'an_id')

    @patch("onapp2vhi.inc.network_onapp.OnAppRequests")
    def test_get_failed(self, mock_onapprequests_ctor):
        mock_response = []
        self.mock_onapprequests.get.return_value = mock_response
        mock_onapprequests_ctor.return_value = self.mock_onapprequests

        result = get_network_id_by_identifier(self.mock_config, "a_network_identifier")

        self.mock_onapprequests.get.assert_called_with('settings/networks')
        self.assertEqual(result, '')


class NicHasMultipleIpsTestCase(TestCase):

    def test_any_nic_with_two_addresses(self):
        self.assertTrue(nic_has_multiple_ips({
            1: ['185.146.85.168', '89.39.209.145'],
            2: ['192.168.1.146'],
        }))

    def test_one_address_per_nic(self):
        self.assertFalse(nic_has_multiple_ips({
            1: ['89.39.209.145'],
            2: ['192.168.1.146'],
        }))

    def test_empty(self):
        self.assertFalse(nic_has_multiple_ips({}))
        self.assertFalse(nic_has_multiple_ips(None))
