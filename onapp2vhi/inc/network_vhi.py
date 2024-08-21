import re
import json
from json.decoder import JSONDecodeError
import ipaddress

from onapp2vhi.inc.ssh_connector import SSH
from onapp2vhi.utilities.config import OnApp2VHIConfig
from onapp2vhi.utilities.regex import JSON_REGEX
from onapp2vhi.utilities.logs.logger import OnAppVHILogger

logs = OnAppVHILogger()


#TODO: refactor this to use VinfraServiceComputeNetwork
class Network:
    def __init__(self, cfg: OnApp2VHIConfig, **kwargs):
        self._ssh = SSH(host=cfg.vhi_conf['cp_ip'],
                        port=int(cfg.vhi_conf['cloud_ssh_port']),
                        ssh_key=cfg.ssh_key)
        self.vinfra_project = kwargs.get('vinfra_project', '')
        self._vinfra_options = f'{cfg.DOMAIN_AUTH} --vinfra-domain="{cfg.vhi_conf["vinfra_domain"]}"' \
                               f' --vinfra-project="{self.vinfra_project}"'

        self.id = kwargs.get("id", "")
        self.name = kwargs.get("name", "")

        # CIDR <-  IP_net
        self.cidr = kwargs.get("cidr", None)
        # The virtual DHCP service will work only within the current network and not be exposed to other networks.
        self.use_dhcp = kwargs.get("use_dhcp", True)
        self.gateway = kwargs.get("gateway", None)
        self.start_address = kwargs.get("start_address", None)
        self.end_address = kwargs.get("end_address", None)
        # DNS_SERVER <- Resolvers
        self.dns_nameservers = kwargs.get("dns_nameservers", [])
        self.ip_version = kwargs.get("ip_version", None)
        self.rbac_policies = kwargs.get("rbac_policies", [])
        # ip_addresses
        self.ip_addresses = kwargs.get("ip_addresses", [])
        # mac_address_of_interface
        self.mac_address = kwargs.get("mac_address", "")

        # physical network
        self.primary = kwargs.get("primary", False)

    def update(self, response):
        for key, value in response.items():
            setattr(self, key, value)

    def get_detail(self):
        network_info_cmd = f"service compute network show {self.id} -f json"
        exit_status, output = self._ssh.execute(network_info_cmd)
        if not exit_status:
            response = output.split('\n')
            response = json.loads("\n".join(response[:-2]))
            return response
        return False

    def is_present(self) -> bool:
        cmd = f"{self._vinfra_options} service compute network list --long -f json"
        exit_status, output = self._ssh.execute(cmd)
        if not exit_status:
            try:
                m = JSON_REGEX.match(output)
                if not m:
                    print(f"Failed to parse json.\n {output}")
                    return False

                response = json.loads(m.group(0))
            except json.decoder.JSONDecodeError as error:
                print(f"Failed to parse JSON.\n {error}")
                return False

            for network in response:
                for subnet in network["subnets"]:
                    if subnet["cidr"] == self.cidr and subnet["allocation_pools"]:
                        for pool in subnet["allocation_pools"]:
                            start = pool["start"]
                            end = pool["end"]

                            if (start == self.start_address) and (
                                end == self.end_address
                            ):
                                self.id = network["id"]
                                return True
        return False

    def is_ips_in_range(self) -> bool:
        logs.info(f'searching: {self.cidr}')
        ip_addresses = set(ipaddress.ip_address(ip_addr) for ip_addr in self.ip_addresses)

        cmd = f"{self._vinfra_options} service compute network list --long -f json"
        exit_status, output = self._ssh.execute(cmd)
        if not exit_status:
            try:
                m = JSON_REGEX.match(output)
                if not m:
                    print(f"Failed to parse json.\n {output}")
                    return False

                response = json.loads(m.group(0))
            except json.decoder.JSONDecodeError as error:
                print(f"Failed to parse JSON.\n {error}")
                return False

            for network in response:
                validated_ip_addresses = set()

                if self.cidr == network['cidr']:
                    logs.info(f'checking: {network["cidr"]}, {network["id"]}')
                    for subnet in network["subnets"]:
                        if subnet["allocation_pools"]:
                            for pool in subnet["allocation_pools"]:
                                start = ipaddress.ip_address(pool["start"])
                                end = ipaddress.ip_address(pool["end"])
                                subnet_network = ipaddress.ip_network(subnet["cidr"])

                                for ip_address in ip_addresses:
                                    if ip_address.version == subnet_network.version:
                                        if ip_address >= start and ip_address <= end:
                                            validated_ip_addresses.add(ip_address)
                                        else:
                                            logs.debug(f'{ip_address} not in {subnet_network}')

                    logs.debug(f'{network["cidr"]}: '
                               f'ips validated {validated_ip_addresses}, '
                               f'not validated {ip_addresses - validated_ip_addresses}')

                    if validated_ip_addresses == ip_addresses:
                        logs.info(f'selected: {network["cidr"]}, {network["id"]}')
                        self.id = network['id']
                        return True
                else:
                    logs.info(f'skipping: {network["cidr"]}, {network["id"]}')

        return False

    def create(self):
        cmd = (f"{self._vinfra_options} service compute network create {self.name} --cidr {self.cidr}"
               f" --dns-nameserver {self.dns_nameservers} --allocation-pool {self.start_address}-{self.end_address}"
               f" --no-dhcp --no-gateway -f json")
        exit_status, output = self._ssh.execute(cmd)
        if not exit_status:
            try:
                m = JSON_REGEX.match(output)
                if not m:
                    print(f'Failed to parse JSON.\n {output}')
                    return False

                output = json.loads(m.group(0))
                network_uuid = re.findall('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', output["id"])
                if not network_uuid:
                    print(f"Network has not been created\n {output}")
                    return False
                return network_uuid[0]
            except (JSONDecodeError, KeyError):
                return False
        return False

    def attach_to_virtual_server(self, virtual_server, ip_addresses):
        """
        "service compute server iface attach {ip_addresses}  --network {vhi_network_id} --server {vhi_virtual_server}"
        :param virtual_server:
        :param ip_addresses:
        """
        if ip_addresses:
            ip_addresses = " ".join([f"--fixed-ip ip-address='{ip}'" for ip in ip_addresses])
        cmd = (f"{self._vinfra_options} service compute server iface attach {ip_addresses}"
               f"  --network {self.id} --server {virtual_server} -f json")
        exit_status, output = self._ssh.execute(cmd)
        if not exit_status:
            response = output.split('\n')
            response = json.loads("\n".join(response[:-2]))
            return response['id']
        return False
