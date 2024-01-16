"""
Sample usage
from cp_wrapper import OnAppCP
cp = OnAppCP(user)
cp.get('cdn_resources', 100)

"""
import requests
import json
import yaml
session = requests.Session()

class OnAppCP(object):
    def __init__(self, user):
        config_file = "fixtures/user.yaml"
        self.config = yaml.load(open(config_file).read(), Loader=yaml.FullLoader)
        self.auth = requests.auth.HTTPBasicAuth(self.config[user]['login'], self.config[user]['password'])

    def get_all(self, entity, action=None, returned_json=True):
        """
        Get list of item from the entity
        Example:
        GET /edge_groups.json
        entity = edge_groups

        :param entity:
        :param action:
        :return: json
        """
        return self._cp_api(session.get, entity, action=action, returned_json=returned_json)

    def get(self, entity, entity_id, data=None, action=None, returned_json=True):
        """
        Get item from entity
        Example1:
        GET /cdn_resources/100.json
        entity    = cdn_resources
        entity_id = 100

        Example 2:
        GET /cdn_resources/100/advanced.json
        entity    = cdn_resources
        entity_id = 100
        action    = advanced

        Example 3:
        GET /settings/location_groups/10/cdn_locations.json
        entity    = /settings/location_groups
        entity_id = 10
        action    = cdn_locations

        :param entity:
        :param entity_id:
        :param data:
        :param action:
        :return: json
        """
        return self._cp_api(session.get, entity, entity_id=entity_id, data=data, action=action, returned_json=returned_json)

    def create(self, entity, data):
        """
        Create entity
        Example:
        curl -i -u user:userpass -X POST http://onapp.test/cdn_resources.json
            -H 'Accept: application/json' -H 'Content-type: application/json'
            -d '{"cdn_resource":{"cdn_hostname":"cdn.test.co","resource_type":"HTTP_PULL",
            "cdn_ssl_certificate_id":"ssl_cert_id","edge_group_ids":[1],"origin":"test.origin.com"}}'
        entity = cdn_resources
        data   = {"cdn_resource":{"cdn_hostname":"cdn.test.co","resource_type":"HTTP_PULL",
                  "cdn_ssl_certificate_id":"ssl_cert_id","edge_group_ids":[1],"origin":"test.origin.com"}}

        Example 2:
        curl -i -X POST -H 'Accept: application/json' -H 'Content-type: application/json'
            -u user:userpass -d '{"network":{"label":"Network API TEST 2","network_group_id":3,"vlan":43,"type":"Networking::Network"}}'
            --url http://onapp.test/settings/networks.json
        entity: settings/networks
        data: {"network":{"label":"Network API TEST 2","network_group_id":3,"vlan":43,"type":"Networking::Network"}}

        :param entity:
        :param data:
        :return: json
        """

        return self._cp_api(session.post, entity, data=data)

    def delete(self, entity, entity_id):
        """
        Delete entity
        Example:
        DELETE /edge_servers/:id.json
        entity    = edge_serversadvanced
        entity_id =

        :return: String: Success or Error
        """
        return self._cp_api(session.delete, entity, entity_id=entity_id)

    def update(self, entity, entity_id, data, action=None):
        """
        Edit entity
        Example:
        curl -i -X PUT -u user:userpass -H 'Accept: application/json'
            -H 'Content-type: application/json' --url 'http://onapp.test/cdn_resources/:id.json'
            -d '{"cdn_resource":{"edge_group_ids":["12"],"origin":"1.1.1.1",
                "cdn_hostname":"CORE-3606-2.com", "cdn_ssl_certificate_id":"8"}}'

        :return: String: Success or Error
        """
        return self._cp_api(session.put, entity, data=data, entity_id=entity_id, action=action)

    def search(self, entity, args=None, data=None, filter=False, returned_json=True):
        '''
        Search entity
        Example:
        curl -i -X GET -H 'Accept: application/json' -H 'Content-type: application/json'
            -u user:userpass --url http://onapp.test/cdn_resources.json?q=111.111.111.1
        entity = cdn_resources
        args = 111.111.111.1

        Example2:
        curl -i -X GET -u user:userpass -H 'Accept: application/json' -H 'Content-type: application/json'
            --url "http://onapp.test/cdn_ssl_certificates.json" -d '{"q":"key"}'
        entity = cdn_resources
        data = {"q":"key"}

        :param entity:
        :param args:
        :param data:
        :return: json
        '''
        return self._cp_api(session.get, entity, args=args, data=data, filter=filter, returned_json=returned_json)
    
    def search_with_search_filter(self, entity, args, filter=True,returned_json=True):
        '''
        Search entity with search filter
        Example:
        curl -i -X GET -u user:userpass -H 'Accept: application/json' -H 'Content-type: application/json'
            --url "http://onapp.test/virtual_machines.json?search_filter[user_id]=17"
        entity = virtual_machines
        search_filter = search_filter[user_id]=17
        filter = True

        Example2:
        curl -i -X GET -u user:userpass -H 'Accept: application/json' -H 'Content-type: application/json'
            --url "http://onapp.test/virtual_machines.json?search_filter[user_id]=17&search_filter[hypervisor_id]=1"
        entity = virtual_machines
        search_filter = search_filter[user_id]=17&search_filter[hypervisor_id]=1
        filter = True

        Example3:
        curl -i -X GET -u user:userpass -H 'Accept: application/json' -H 'Content-type: application/json'
            --url "http://onapp.test/templates.json?search_filter[query]=Windows+Server+2016+x64+STD"
        entity = templates
        search_filter = search_filter[query]=Windows+Server+2016+x64+STD
        filter= True

        :param entity:
        :param search_filter:
        :param filter:
        :return: json
        '''
        return self._cp_api(session.get, entity, args=args, filter=filter, returned_json=returned_json)

    def post_action(self, entity, _id, action, data=None, query_string=None):
        """
        Example:
        POST /edge_servers/:edge_server_id/reboot.json
        entity: edge_servers
        _id:
        action: reboot

        Example:
        curl -i -X POST -H 'Accept: application/json' -H 'Content-type: application/json'
            -u user:userpass -d '{"edge_server":{"destination":"1","cold_migrate_on_rollback":"1"}}'
            --url http://onapp.test/edge_servers/:edge_server_id/migrate.json
        entity: edge_servers
        _id:
        action: migrate
        data: {"edge_server":{"destination":"1","cold_migrate_on_rollback":"1"}}

        Example 2:
        POST /settings/networks/:network_id/ip_nets.json
        entity: networks
        _id: 
        sub: ip_nets

        Example 3:
        curl -i -X POST -H 'Accept: application/json' -H 'Content-type: application/json'
            -u user:userpass -d '{"ip_net": {"network_address":"192.168.0.0","network_mask":"24",
            "label":"AutoTestNetworkIpvNet1","default_gateway":"2.2.2.1","add_default_ip_range":"1","gateway_outside_ip_net":"1"}}'
            --url http://onapp.test/settings/networks/12/ip_nets.json
        entity: settings/networks
        _id: 12
        action: ip_nets
        data: {"network":{"label":"Network API TEST 2","network_group_id":3,"vlan":43,"type":"Networking::Network"}}

        Example 4:
        curl -i -X POST -H 'Accept: application/json' -H 'Content-type: application/json'
            -u user:userpass 
            --url http://onapp.test/virtual_machines/1/rebuild_network.json?force=1&shutdown_type=graceful&required_startup=1
        entity: virtual_machines/networks
        _id: 1
        action: rebuild_network
        query_string: force=1&shutdown_type=graceful&required_startup=1

        :param entity:
        :param _id:
        :param action:
        :param data:
        :param query_string:
        :return:
        """
        return self._cp_api(session.post, entity, entity_id=_id, action=action, data=data, query_string=query_string)
    
    def _cp_api(self, requests_func, entity, data=None, entity_id=None, action=None, query_string=None, args=None, filter=False, returned_json=None):
        """
        :param requests_func: session.get or session.post
        :param args: entity. eg: edge_groups, cdn_resource
        :param data: data for post request
        :param action: prefetch, purge,
        :return:
        """
        path = "%s" % entity
        headers = {"Accept": "application/json", "Content-type": "application/json"}
        if entity_id is not None:
            path = "%s/%s" % (entity, entity_id)

        if action is not None:

            if entity_id is not None:
                path = "%s/%s/%s" % (entity, entity_id, action)
            else:
                path = "%s/%s" % (entity, action)

        url = "%s/%s.json" % (self.config["cp_url"], path)

        if action == "rebuild_network":
            url = url + "?%s" % query_string

        if args is not None and not filter:
            url = url + "?q=" + args
        elif args is not None and filter:
            url = url + "?" + args

        response = requests_func(url, data=json.dumps(data), auth=self.auth, headers=headers)

        if returned_json:
            return response.json()
        else:
            return response
