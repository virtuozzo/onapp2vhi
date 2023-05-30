import ipaddress
import os
from inc.onapp_helpers import _spaces
from inc.logger import logs
from os.path import join, dirname, abspath
from inc.network_onapp import (
    get_virtual_server_interfaces,
    get_virtual_server_ip_addresses,
    get_network_nameserver,
    get_ip_net,
)

FILE_NAME = 'scripts/windows_network_{vm_identifier}.bat'
PATH = join(dirname(dirname(abspath(__file__))), FILE_NAME)


class WindowsNetworkReconfig:

    def __init__(self, vm_identifier: str = ''):
        """
        Class is preparing .bat file for only Windows based VM's save file and remove it after using
        :param vm_identifier: 'wbrxpcgdjynpae'
        """
        self.vm_identifier = vm_identifier
        self.add = 'add'
        self.set = 'set'
        self.file = PATH.format(vm_identifier=self.vm_identifier)
        self.primary_ip_address = ''

    @property
    def _head_of_config_file(self):
        """
        Static head of bash script
        :return: str
        """
        head = '''
@echo off

SET "BOARD="
FOR /F "skip=1 delims=" %%I IN (\'wmic Computersystem get Manufacturer\') DO (FOR /F "delims=" %%J IN ("%%I") DO (set "BOARD=%%J")
)

IF /I "%BOARD%"=="Virtuozzo     " (goto V) ELSE (goto END)

:V
        
        '''
        return head

    @property
    def _end_of_config_file(self):
        """
        Static end of bash script
        :return: str
        """
        return f'''
:END

ping -n 1 {self.primary_ip_address} | find /I "TTL=" >nul
if ERRORLEVEL 0 (DEL /q /f c:\\onapp.bat)

:END

        '''

    def convert_netmask(self, netmask_prefix: int) -> str:
        """
        Convert netmask into dot value 24 > "255.255.255.0"
        :param netmask_prefix: 24
        :return:
        """
        return str(ipaddress.IPv4Network('0.0.0.0/' + str(netmask_prefix)).netmask)

    def _prepare_ip_address(self, method: str = '', ipv4=False, **kwargs) -> str:
        """
        Prepare short piece of string with properties set in kwargs
        :param kwargs: {'ip': '10.63.0.134',
                        'mask': '255.255.255.0',
                        'mac_space': '00 16 3e 70 33 9d',
                        'mac_dash': '00-16-3e-70-33-9d',
                        'gateway': '10.63.0.1'}
        :param method:  "add" - secondary IP
                        "set" - when first IP addr
        :param ipv6: True or False
        :return:
        """
        gateway = kwargs['gateway']
        if gateway:
            gateway = f'gateway={kwargs["gateway"]} gwmetric=1'
        if ipv4:
            source_static = ''
            if method != self.add:
                source_static = 'source=static'

            _address = f'''
ping -n 5 127.0.0.1

IF NOT EXIST C:\Windows\System32\DriverStore (
FOR /f "usebackq tokens=1,2 delims=,_"  %%a IN (`"getmac /v /FO CSV | C:\Windows\System32\\find.exe /I "{kwargs["mac_dash"]}""`) DO netsh interface ip {method} address name=%%a {source_static} addr={kwargs["ip"]} mask={kwargs["mask"]} {gateway}
) ELSE (
FOR /F "usebackq tokens=1-13,* delims=.-: " %%a IN (`"route print | C:\Windows\System32\\find.exe /I "{kwargs["mac_space"]}""`) DO netsh interface ip {method} address name=%%a {source_static} addr={kwargs["ip"]} mask={kwargs["mask"]} {gateway}
)

            '''
            return _address

        else:
            method = self.add
            _address = f'''
ping -n 5 127.0.0.1

IF NOT EXIST C:\Windows\System32\DriverStore (
FOR /f "usebackq tokens=1,2 delims=,_"  %%a IN (`"getmac /v /FO CSV | C:\Windows\System32\\find.exe /I "{kwargs["mac_dash"]}""`) DO netsh interface ipv6 {method} address interface=%%a address={kwargs["ip"]}/{kwargs["prefix"]}
) ELSE (
FOR /F "usebackq tokens=1-13,* delims=.-: " %%a IN (`"route print | C:\Windows\System32\\find.exe /I "{kwargs["mac_space"]}""`) DO netsh interface ipv6 {method} address interface=%%a address={kwargs["ip"]}/{kwargs["prefix"]} store=persistent
)

            '''
            return _address

    def _prepare_ipv6_gateway(self, **kwargs) -> str:
        """
        Prepare short piece of string with properties set in kwargs
        :param kwargs: {'mac_dash': '00-16-3e-70-33-9d',
                        'mac_space': '00 16 3e 70 33 9d',
                        'gateway': '2001:610:148:dead::1'}
        :return:
        """
        _gateway = f'''
ping -n 5 127.0.0.1

IF NOT EXIST C:\Windows\System32\DriverStore (FOR /f "usebackq tokens=1,2 delims=,_"  %%a IN (`"getmac /v /FO CSV | C:\Windows\System32\\find.exe /I "{kwargs["mac_dash"]}""`) DO netsh interface ipv6 add route ::/0 interface=%%a nexthop={kwargs["gateway"]} metric=0
) ELSE (
FOR /F "usebackq tokens=1-13,* delims=.-: " %%a IN (`"route print | C:\Windows\System32\\find.exe /I "{kwargs["mac_space"]}""`) DO netsh interface ipv6 add route ::/0 interface=%%a nexthop={kwargs["gateway"]} metric=0 store=persistent
)

        '''
        return _gateway

    def _prepare_dns(self, ipv4=False, **kwargs) -> str:
        """
        Prepare short piece of string with properties set in kwargs
        :param kwargs: {'ip': '10.63.0.134',
                        'mac_dash': '00-16-3e-70-33-9d',
                        'mac_space': '00 16 3e 70 33 9d',
                        'dns': '8.8.4.4'}
        :param ipv6: True or False
        :return:
        """
        if ipv4:
            _address = f'''
ping -n 5 127.0.0.1

IF NOT EXIST C:\Windows\System32\DriverStore (
FOR /f "usebackq tokens=1,2 delims=,_"  %%a IN (`"getmac /v /FO CSV | C:\Windows\System32\\find.exe /I "{kwargs["mac_dash"]}""`) DO netsh interface ip set dns %%a dhcp && netsh interface ip add dns %%a {kwargs["dns"]}
) ELSE (
FOR /F "usebackq tokens=1-13,* delims=.-: " %%a IN (`"route print | C:\Windows\System32\\find.exe /I "{kwargs["mac_space"]}""`) DO netsh interface ip set dns %%a dhcp && netsh interface ip add dns %%a {kwargs["dns"]}
)
            
            '''
            return _address

        else:
            _address = f'''
ping -n 5 127.0.0.1
    
IF NOT EXIST C:\Windows\System32\DriverStore (
FOR /f "usebackq tokens=1,2 delims=,_"  %%a IN (`"getmac /v /FO CSV | C:\Windows\System32\\find.exe /I "{kwargs["mac_dash"]}""`) DO netsh interface ipv6 add dnsservers name=%%a {kwargs["dns"]}
) ELSE (
FOR /F "usebackq tokens=1-13,* delims=.-: " %%a IN (`"route print | C:\Windows\System32\\find.exe /I "{kwargs["mac_space"]}""`) DO netsh interface ipv6 add dns name=%%a {kwargs["dns"]}
)
            
            '''
            return _address

    def _collect_vm_network_data(self):
        logs.info(msg=f'{_spaces} -- Collecting network params for VM [{self.vm_identifier}]', header=True)
        vm_networks = []
        vm_nics = get_virtual_server_interfaces(virtual_server_id=self.vm_identifier)

        for nic in vm_nics:
            _network = {}
            _nic = nic["network_interface"]
            _nic_id = _nic["id"]
            ip_addresses = get_virtual_server_ip_addresses(virtual_server_id=self.vm_identifier,
                                                           network_interface_id=_nic_id)
            _network['primary'] = _nic['primary']
            _network['mac_dash'] = _nic['mac_address'].replace(':', '-')
            _network['mac_space'] = _nic['mac_address'].replace(':', ' ')
            ip_addr = [
                {k: v for k, v in addr.items() if k in
                 ["address", "gateway", "primary", "network_id", "ip_net_id", "ipv4", "prefix"]} for addr in
                ip_addresses
            ]
            ip_addr.sort(key=lambda x: not x["primary"])
            _network['ip_addr_info'] = ip_addr
            network_id = _network['ip_addr_info'][0]['network_id']
            _ip_net = get_ip_net(network_id=network_id,
                                 ip_net_id=_network['ip_addr_info'][0]['ip_net_id'])
            if _network['primary']:
                for num, _ip_addr in enumerate(_network['ip_addr_info']):
                    if _ip_addr['primary'] and not _ip_addr['ipv4']:
                        logs.error(msg=f'VM [{self.vm_identifier} | {_ip_addr["address"]}]'
                                       f' has primary IPv6 address in the Primary NIC.'
                                       f' IPv6 cannot be primary IP addr in primary NIC. Please re-assign IP order!!!')
                        return []

                    elif _ip_addr['primary'] and _ip_addr['ipv4']:
                        # Set Primary IP Address for class
                        self.primary_ip_address = ip_addr[0]['address']
                        _network['dns_ipv4'] = get_network_nameserver(network_id=network_id,
                                                                      ipv4=_network['ip_addr_info'][num]['ipv4'])

            for num, _ip_addr in enumerate(_network['ip_addr_info']):
                if _ip_addr["ipv4"]:
                    _network['ip_addr_info'][num]['ipv4_mask'] = self.convert_netmask(
                        netmask_prefix=_ip_net['ip_net']['network_mask']
                    )
                elif not _ip_addr["ipv4"]:
                    _network['ip_addr_info'][num]['ipv6_mask'] = _ip_addr["prefix"]
                    _network['dns_ipv6'] = get_network_nameserver(network_id=network_id,
                                                                  ipv4=_network['ip_addr_info'][num]['ipv4'])

            vm_networks.append(_network)
        vm_networks.sort(key=lambda x: not x["primary"])
        return vm_networks

    def create_file(self):
        """
        Creates .bat file with proper configuration for Windows based Virtual Machine and
          save it into /scripts folder
        :return:
        """
        vm_networks = self._collect_vm_network_data()
        if not vm_networks:
            return False

        _middle_script = ''
        logs.info(msg=f'{_spaces} -- Preparing .BAT script for VM [{self.vm_identifier}] -- ', header=True)
        for num, _network in enumerate(vm_networks):
            ip_addr_count = []
            for ip_addr in _network['ip_addr_info']:
                _dns_part = ''
                ipv6_gateway = ''

                # Set Up DNS
                if _network['primary'] and ip_addr['ipv4']:
                    dns_props = {'mac_dash': _network['mac_dash'],
                                 'mac_space': _network['mac_space'],
                                 'dns': _network['dns_ipv4']}
                    if ip_addr['primary'] and _network['dns_ipv4']:
                        _dns_part += self._prepare_dns(ipv4=True, **dns_props)

                if not ip_addr['ipv4'] and 6 not in ip_addr_count:
                    dns_props = {'mac_dash': _network['mac_dash'],
                                 'mac_space': _network['mac_space'],
                                 'dns': _network['dns_ipv6'],
                                 'gateway': ip_addr['gateway']}
                    if _network['dns_ipv6']:
                        _dns_part += self._prepare_dns(ipv4=False, **dns_props)
                    ipv6_gateway += self._prepare_ipv6_gateway(**dns_props)

                # Set Up Method in File
                _method = self.add
                if ip_addr['ipv4']:
                    if ip_addr['primary']:
                        _method = self.set
                elif not ip_addr['ipv4']:
                    if 6 not in ip_addr_count:
                        _method = self.set
                gateway = ''

                # Set Up Gateway
                if ip_addr['ipv4']:
                    if _network['primary'] and ip_addr['primary']:
                        gateway = ip_addr['gateway']
                    else:
                        gateway = ipv6_gateway

                # Set Up Network Mask
                _mask = ''
                if ip_addr['ipv4']:
                    if 'ipv4_mask' in ip_addr.keys():
                        _mask = ip_addr['ipv4_mask']
                else:
                    _mask = ip_addr['ipv6_mask']

                # Build properties for string
                _ip_props = {'ip': ip_addr['address'],
                             'mask': _mask,
                             'mac_space': _network['mac_space'],
                             'mac_dash': _network['mac_dash'],
                             'gateway': gateway,
                             'prefix': ip_addr['prefix']}
                ip_addr_part = self._prepare_ip_address(method=_method,
                                                        ipv4=ip_addr['ipv4'],
                                                        **_ip_props)

                # Concatenate strings ip address, gateway, dns
                _middle_script += ip_addr_part
                _middle_script += _dns_part
                if not ip_addr['ipv4']:
                    _middle_script += ipv6_gateway
                if ip_addr['ipv4']:
                    ip_addr_count.append(4)
                else:
                    ip_addr_count.append(6)
        logs.debug(
            msg=f'Prepared `.bat` script for windows VM [{self.vm_identifier}]:\n{_middle_script}', separator=True
        )
        whole_script = f"{self._head_of_config_file}{_middle_script}{self._end_of_config_file}"
        with open(self.file, 'w+', encoding='utf=8') as _bat_file:
            _bat_file.write(whole_script)
            logs.info(msg=f'File with new Windows Network config created: {self.file}', header=True)
        return True

    def delete_file(self):
        """
        Delete created file
        :return:
        """
        if os.path.isfile(self.file):
            os.remove(self.file)
            logs.info(msg=f"{self.file} has been deleted.", header=True)
        else:
            logs.warn(msg=f"{self.file} does not exist.")
