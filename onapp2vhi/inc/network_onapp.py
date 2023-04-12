from onapp2vhi.inc.rest_client import OnAppRequests
from onapp2vhi.inc.logger import logs
from typing import Dict, List

request_handler = OnAppRequests()

TIMEOUT = 20


class NetworkInterface:
    def __init__(self, **kwargs):
        self.virtual_server_id = kwargs.get("virtual_server_id", "")
        self.hypervisor_id = kwargs.get("hypervisor_id", "")
        self.network_join_identifier = kwargs.get("network_join_identifier", "")
        self.network_identifier = kwargs.get("network_identifier", "")
        self.ip_net = kwargs.get("ip_net", "")
        self.ip_range = kwargs.get("ip_range", "")
        self.network_nameserver = kwargs.get("network_nameserver", "")
        self.ip_addresses = kwargs.get("ip_addresses", [])
        self.ipv4 = kwargs.get("ipv4", False)
        self.primary = kwargs.get("primary", False)
        self.mac_address = kwargs.get("mac_address", "")
        self.label = f"network_{self.network_identifier}"

    def __repr__(self):
        return self.label


class NetworkInterfaces:
    def __init__(self):
        self._network_interfaces = []

    def add(self, network_interface):
        self._network_interfaces.append(network_interface)

    def get_all(self):
        return self._network_interfaces

    def get_by_network_join(self, network_join_identifier):
        logs.info(self._network_interfaces)
        return next(
            (
                network
                for network in self._network_interfaces
                if network.network_join_identifier == network_join_identifier
            ),
            None,
        )

    def __len__(self):
        return len(self._network_interfaces)


def get_virtual_server_hypervisor(virtual_server_id: str) -> str:
    """
    Get the virtual server hypervisor id
    :param virtual_server_id: The virtual server id
    :return str | bool: The hypervisor ID which the virtual server belongs
    """
    _url = f"virtual_machines/{virtual_server_id}"
    _virtual_server = request_handler.get(_url)
    if _virtual_server:
        return _virtual_server["virtual_machine"]["hypervisor_id"]
    return False


def get_hypervisor_group_id(hypervisor_id: str) -> str:
    _hypervisor = request_handler.get(f"settings/hypervisors/{hypervisor_id}")
    if _hypervisor:
        return _hypervisor["hypervisor"]["hypervisor_group_id"]
    return ''


def get_hypervisor_network_join(hypervisor_id: str, network_join_id: str) -> str:
    """
    Get the network assigned to the hypervisor
    :param hypervisor_id: The hypervisor ID which the VM belongs
    :param network_join_id: Network join identifier from VM
    :return str: Contain the network identifier
    """
    _network_joins = request_handler.get(f"settings/hypervisors/{hypervisor_id}/network_joins")
    if _network_joins:
        return next((
                network_join["network_join"]["identifier"]
                for network_join in _network_joins
                if network_join["network_join"]["id"] == network_join_id
            ), ''
        )


def get_hypervisor_group_network_join(hypervisor_group_id: str, network_join_id: str) -> str:
    """
    Get the network assigned to the hypervisor
    :param hypervisor_group_id: The compute service zone ID which the VM belongs
    :param network_join_id: Network join identifier from VM
    :return str: Contain the network identifier
    """
    _network_joins = request_handler.get(f"settings/hypervisor_zones/{hypervisor_group_id}/network_joins")
    return next(
        (
            network_join["network_join"]["identifier"]
            for network_join in _network_joins
            if network_join["network_join"]["id"] == network_join_id
        ),
        False,
    )


def get_virtual_server_interfaces(virtual_server_id: str) -> List[Dict[str, str]]:
    """
    Get the VS network interfaces
    :param virtual_server_id: The virtual server ID
    :return List[Dict[str:str]: Contain the VS IP address.
    """
    _network_interfaces = request_handler.get(f"virtual_machines/{virtual_server_id}/network_interfaces")
    if _network_interfaces:
        return _network_interfaces
    return []


def get_virtual_server_ip_addresses(virtual_server_id: str, network_interface_id: str) -> List:
    """
    Get the VS IP addresses related to network interface
    :param virtual_server_id: The virtual server ID
    :param network_interface_id: Network ID to which this nameserver belongs
    :return List[str]: Contain the VS IP address.
    """
    _ip_address_join = request_handler.get(f"virtual_machines/{virtual_server_id}/ip_addresses")
    return [
        ip_address_join["ip_address_join"]["ip_address"]
        for ip_address_join in _ip_address_join
        if ip_address_join["ip_address_join"]["network_interface_id"]
        == network_interface_id
    ]


def get_network_nameserver(network_id: str, ipv4=True) -> str:
    """
    Get the DNS network network address
    :param network_id: Network ID to which this nameserver belongs
    :param ipv4: get
    :return str: Contain the DNS IP address.
    Here are some popular IPv4 and IPv6 DNS resolvers:

        IPv4 DNS Resolvers:
        Google Public DNS: IPv4 Address 8.8.8.8 and 8.8.4.4
        Cloudflare DNS: IPv4 Address 1.1.1.1 and 1.0.0.1
        OpenDNS: IPv4 Address 208.67.222.222 and 208.67.220.220

        IPv6 DNS Resolvers:
        Google Public DNS: IPv6 Address 2001:4860:4860::8888 and 2001:4860:4860::8844
        Cloudflare DNS: IPv6 Address 2606:4700:4700::1111 and 2606:4700:4700::1001
        OpenDNS: IPv6 Address 2620:119:35::35 and 2620:119:53::53
        These resolvers can be used to resolve DNS queries for domain names in either IPv4 or IPv6 format.
    """
    _nameservers = request_handler.get(f"settings/nameservers")
    addresses = [nameserver["nameserver"]["address"] for nameserver in _nameservers
                 if nameserver["nameserver"]["network_id"] == int(network_id)]
    for address in addresses:
        if ipv4 and '.' in address:
            logs.info(msg=f'Found resolver for IPv4 [{address}]')
            return address

        elif not ipv4 and ':' in address:
            logs.info(msg=f'Found resolver IPv6 [{address}]')
            return address

    logs.warn(msg=f'Resolver not found for Network ID [{network_id}] IPv4: {ipv4}')
    return ''


def get_network_interfaces(virtual_server_id: str):
    """
    Get the all network interfaces assigned to VM
    :param virtual_server_id: The virtual server identifier
    :return list: Contain the all network interfaces assigned to VM.
    """
    _get_network_join = request_handler.get(f"virtual_machines/{virtual_server_id}/network_interfaces")
    if _get_network_join:
        return _get_network_join
    return False


def get_ip_net(network_id: str, ip_net_id: str):
    """Get the network IP nets
    :param network_id: Network ID to which this IP net belongs
    :param ip_net_id: The ID of the IP net
    :return dict: Contain ranges of IP addresses.
    """
    _ip_net = request_handler.get(f"settings/networks/{network_id}/ip_nets/{ip_net_id}")
    if _ip_net:
        return _ip_net
    return False


def get_ip_range(network_id: str, ip_net_id: str, ip_range_id: str) -> Dict:
    """
    Get the network IP rage
    :param network_id: Network ID to which this IP net belongs
    :param ip_net_id: The ID of the IP net
    :param ip_range_id: The ID of the IP range
    :return dict: Contain of IP addresses.
    """
    _ip_range = request_handler.get(f"settings/networks/{network_id}/ip_nets/{ip_net_id}/ip_ranges/{ip_range_id}")
    if _ip_range:
        return _ip_range
    return _ip_range


def get_network_id_by_identifier(identifier: str) -> str:
    """
    :param identifier:  the network identifier used on hypervisor join
    :return: network ID
    """
    _network = request_handler.get(f"settings/networks")
    return next(
        (
            network["network"]["id"]
            for network in _network
            if network["network"]["identifier"] == identifier
        ),
        '',
    )
