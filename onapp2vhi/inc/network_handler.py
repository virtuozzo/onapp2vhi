from onapp2vhi.inc.network_vhi import Network
from onapp2vhi.inc.onapp_helpers import onapp_version
from onapp2vhi.utilities.logs.logger import OnAppVHILogger
from onapp2vhi.inc.network_onapp import (
    NetworkInterface,
    NetworkInterfaces,
    get_ip_range,
    get_ip_net,
    get_network_nameserver,
    get_network_id_by_identifier,
    get_virtual_server_ip_addresses,
    get_virtual_server_interfaces,
    get_virtual_server_hypervisor,
    get_hypervisor_group_network_join,
    get_hypervisor_group_id,
    get_hypervisor_network_join,
)
from onapp2vhi.utilities.config import OnApp2VHIConfig
from onapp2vhi.ops.error import MigrationError

logs = OnAppVHILogger()


def ordered_nic_ip_addresses(vs_ip_addresses):
    """Return IP dicts with OnApp primary first, duplicates removed, order preserved.

    OnApp 6.4+ (including 6.5/6.6) sets `primary` on the IP itself, not as list
    position. Older releases omit the flag; then API order is kept.
    """
    if not vs_ip_addresses:
        return []
    primaries = [ip for ip in vs_ip_addresses if ip.get("primary")]
    others = [ip for ip in vs_ip_addresses if not ip.get("primary")]
    ordered = primaries + others if primaries else list(vs_ip_addresses)
    unique = []
    seen = set()
    for ip in ordered:
        addr = ip.get("address")
        if not addr or addr in seen:
            continue
        seen.add(addr)
        unique.append(ip)
    return unique


def get_network_configuration(cfg: OnApp2VHIConfig,
                              virtual_server_identifier: str,
                              vinfra_project: str,
                              strict_ip_pool_match: bool = False,
                              no_network_create: bool = False) -> str:
    networks_cmd = []
    version = onapp_version(cfg)
    vs_network_interfaces = NetworkInterfaces()
    virtual_server_hypervisor_id = get_virtual_server_hypervisor(cfg, virtual_server_identifier)
    hv_group_id = get_hypervisor_group_id(cfg, virtual_server_hypervisor_id)
    virtual_server_nic = get_virtual_server_interfaces(cfg, virtual_server_identifier)

    for nic in virtual_server_nic:
        data = {}
        network_join = get_hypervisor_network_join(
            cfg, virtual_server_hypervisor_id, nic["network_interface"]["network_join_id"]
        )
        if not network_join:
            logs.debug("The network is assigned to Compute Zone only", separator=True)
            network_join = get_hypervisor_group_network_join(
                cfg,
                hv_group_id,
                nic["network_interface"]["network_join_id"]
            )
        network_identifier, _ = network_join.split('-')
        nic_id = nic["network_interface"]["id"]
        vs_ip_addresses = get_virtual_server_ip_addresses(cfg, virtual_server_identifier, nic_id)
        if not vs_ip_addresses:
            logs.warn(f'IP addresses are not assigned to network interface with ID: {nic_id}')
            continue

        ordered_ips = ordered_nic_ip_addresses(vs_ip_addresses)
        if version > 6.3 and not any(ip.get("primary") for ip in vs_ip_addresses):
            logs.warn(
                f'The primary IP is not found; the following IP will be set as primary: {ordered_ips[0]["address"]}'
            )
        lead_ip = ordered_ips[0]
        data['network_identifier'] = network_identifier
        data["ipv4"] = lead_ip.get("ipv4", False)
        data["primary"] = True if nic['network_interface']['primary'] else False
        data["ip_addresses"] = [ip_address['address'] for ip_address in ordered_ips]
        data["mac_address"] = nic["network_interface"]["mac_address"]
        data["network_id"] = get_network_id_by_identifier(cfg, network_identifier)
        data['network_nameserver'] = get_network_nameserver(cfg, data['network_id'], ipv4=True)
        data["ip_net_id"] = lead_ip['ip_net_id']
        data["ip_range_id"] = lead_ip['ip_range_id']
        data['ip_net'] = get_ip_net(cfg, data['network_id'], data['ip_net_id'])
        data['ip_range'] = get_ip_range(cfg, data['network_id'], data['ip_net_id'], data["ip_range_id"])
        nic = NetworkInterface(**data)
        vs_network_interfaces.add(nic)

    for network in vs_network_interfaces.get_all():
        logs.debug(f'processing {network}')
        vhi_network = Network(
            cfg,
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
        logs.debug(f'network_ip_addresses = {network.ip_addresses}')

        ip_addresses = "".join([f"fixed-ip='{ip}'," for ip in network.ip_addresses])

        if (strict_ip_pool_match and vhi_network.is_present()) or \
           (not strict_ip_pool_match and vhi_network.is_ips_in_range()):
            # use the network
            network_interface_cmd = f" --network id={vhi_network.id},{ip_addresses}mac='{vhi_network.mac_address}'," \
                                    f"spoofing-protection-disable "
            if network.primary:
                logs.info("The virtual server primary interface has been found", header=True)
                networks_cmd.insert(0, network_interface_cmd)
            else:
                networks_cmd.append(network_interface_cmd)
        elif not no_network_create:
            # create new network and use that instead
            logs.warn(f"The Network not found: {vhi_network.cidr}")
            if vhi_network.ip_version == 6:
                logs.error(
                    f"The {vhi_network.cidr} won't be used. Please configure the IPv6 physical network"
                    f" or remove {ip_addresses} from virtual server: {virtual_server_identifier}"
                )
                return False

            vhi_network_id = vhi_network.create()
            network_cmd = (f" --network id={vhi_network_id},{ip_addresses}"
                           f"mac='{vhi_network.mac_address}',"
                           "spoofing-protection-disable ")
            networks_cmd.append(network_cmd)
        else:
            raise MigrationError(f'Network {vhi_network.cidr} not found with --strict-ip-pool-check={strict_ip_pool_match} and --no-network-create={no_network_create}')

        logs.debug(f'networks command = {networks_cmd}')
    return ''.join(networks_cmd)
