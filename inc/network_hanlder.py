from inc.network_vhi import Network
from inc.onapp_helpers import onapp_version
from inc.network_onapp import *
from inc.logger import logs


def get_network_configuration(virtual_server_identifier: str, vinfra_project: str):
    data = {}
    networks_cmd = []
    version = onapp_version()
    vs_network_interfaces = NetworkInterfaces()
    virtual_server_hypervisor_id = get_virtual_server_hypervisor(virtual_server_identifier)
    hv_group_id = get_hypervisor_group_id(virtual_server_hypervisor_id)
    virtual_server_nic = get_virtual_server_interfaces(virtual_server_identifier)

    for nic in virtual_server_nic:
        network_join = get_hypervisor_network_join(
            virtual_server_hypervisor_id, nic["network_interface"]["network_join_id"]
        )
        if not network_join:
            logs.debug("The network is assigned to Compute Zone only", separator=True)
            network_join = get_hypervisor_group_network_join(
                hv_group_id,
                nic["network_interface"]["network_join_id"]
            )
        network_identifier, _ = network_join.split('-')
        nic_id = nic["network_interface"]["id"]
        vs_ip_addresses = get_virtual_server_ip_addresses(virtual_server_identifier, nic_id)
        if not vs_ip_addresses:
            logs.warn(f'IP addresses are not assigned to network interface with ID: {nic_id}')
            continue

        data['network_identifier'] = network_identifier
        data["ipv4"] = next((ip_address['ipv4'] for ip_address in vs_ip_addresses), False)
        if version <= 6.0 and nic['network_interface']['primary'] is True:
            data["primary_ip"] = [vs_ip_addresses[0]['address']]
        elif version > 6.0:
            data["primary_ip"] = [
                ip_address['address'] for ip_address in vs_ip_addresses
                if ip_address["primary"]
            ]
        data["primary"] = True if nic['network_interface']['primary'] else False
        data["ip_addresses"] = [ip_address['address'] for ip_address in vs_ip_addresses
                                if ip_address['address'] != data["primary_ip"]]
        data["mac_address"] = nic["network_interface"]["mac_address"]
        data["network_id"] = get_network_id_by_identifier(network_identifier)
        data['network_nameserver'] = get_network_nameserver(data['network_id'], ipv4=True)
        data["ip_net_id"] = next((ip_address['ip_net_id'] for ip_address in vs_ip_addresses))
        data["ip_range_id"] = next((ip_address['ip_range_id'] for ip_address in vs_ip_addresses))
        data['ip_net'] = get_ip_net(data['network_id'], data['ip_net_id'])
        data['ip_range'] = get_ip_range(data['network_id'], data['ip_net_id'], data["ip_range_id"])
        if data["primary_ip"]:
            data["ip_addresses"].insert(0, data["primary_ip"][0])  # the primary IP should be first
        else:
            logs.warn(
                f'The primary IP is not found the following IP will be set as primary: {data["ip_addresses"][0]}'
            )
        nic = NetworkInterface(**data)
        vs_network_interfaces.add(nic)

    for network in vs_network_interfaces.get_all():
        vhi_network = Network(
            id='',
            name=f"network_{network.network_identifier}",
            vinfra_project=vinfra_project,
            rbac_policies=[],
            ip_addresses=network.ip_addresses,
            mac_address=network.mac_address,
            primary=network.primary,
            start_address=network.ip_range['ip_range']['start_address'],
            end_address=network.ip_range['ip_range']['end_address'],
            cidr=f"{network.ip_net['ip_net']['network_address']}/{network.ip_net['ip_net']['network_mask']}",
            dns_nameservers="8.8.8.8" if not network.network_nameserver else network.network_nameserver,
            enable_dhcp=True,  # set True by default for virtual networks
            gateway=network.ip_range['ip_range']['default_gateway'],
            ip_version=4 if network.ipv4 else 6,
        )
        if not network.ip_addresses:
            logs.warn("Network interface without IP address. It won't be used")
            continue

        ip_addresses = "".join([f"fixed-ip='{ip}'," for ip in network.ip_addresses])
        if not vhi_network.is_present():
            logs.warn(f"The Network not found: {vhi_network.cidr}")
            if vhi_network.ip_version == 6:
                logs.error(
                    f"The {vhi_network.cidr} won't be used. Please configure the IPv6 physical network"
                    f" or remove {ip_addresses} from virtual server: {virtual_server_identifier}"
                )
                return False

            vhi_network_id = vhi_network.create()
            secondary_network_cmd = (f" --network id={vhi_network_id},{ip_addresses}"
                                     f"mac='{vhi_network.mac_address}',spoofing-protection-disable ")
            networks_cmd.append(secondary_network_cmd)
        else:
            network_interface_cmd = f" --network id={vhi_network.id},{ip_addresses}mac='{vhi_network.mac_address}'," \
                                    f"spoofing-protection-disable "
            if network.primary:
                logs.info("The virtual server primary interface has been found", header=True)
                networks_cmd.insert(0, network_interface_cmd)
            else:
                networks_cmd.append(network_interface_cmd)
    return ''.join(networks_cmd)
