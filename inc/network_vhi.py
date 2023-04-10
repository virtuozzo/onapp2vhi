from onapp2vhi.utility.config import OnApp2VHIConfig
from inc.ssh_connector import SSH
import json

cfg = OnApp2VHIConfig()

class Network:
    def __init__(self, **kwargs):
        self._config = cfg.get_config(cp_type="vhi")
        self._ssh = SSH(host=self._config.cp_ip, port=self._config.cloud_ssh_port)
        self._vinfra_project = kwargs.get("vinfra_project", self._config.vinfra_project)
        self._vinfra_options = f'{cfg.DOMAIN_AUTH} --vinfra-domain="{self._config.vinfra_domain}"' \
                               f' --vinfra-project="{self._vinfra_project}"'

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

    def is_present(self):
        cmd = f"{cfg.VINFRA_AUTH} service compute network list -f json"
        exit_status, output = self._ssh.execute(cmd)
        if not exit_status:
            response = output.split('\n')
            response = json.loads("\n".join(response[:-2]))
            for network in response:
                if network['cidr'] == self.cidr:
                    self.id = network['id']
                    return True
        return False

    def create(self):
        cmd = (f"{self._vinfra_options} service compute network create {self.name} --cidr {self.cidr}"
               f" --dns-nameserver {self.dns_nameservers} --allocation-pool {self.start_address}-{self.end_address}"
               f"--no-dhcp --no-gateway -f json | jq -r \".id\"")
        exit_status, output = self._ssh.execute(cmd)
        if not exit_status:
            response = output.split('\n')[0]
            return response['id']
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
