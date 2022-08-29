'''
This is a simple example of using the openstack python api bindings to 
communicate with a running openstack system.
Requirements:  python, python-heatclient, python-novaclient, etc.
To use interactively, first obtain an openstack rcfile from your system
and source it to set your env vars.
Open python in a terminal session and type:
import openstack_ex
Now type:
openstack_ex.list_users()
You should get a list of users back from the console.  Other methods work the 
same way.
'''

import os
import pprint

from keystoneclient.auth.identity import v2
from keystoneclient import session as ksc_session
from keystoneclient.v3 import client as keystone_v3
from novaclient.v2 import client as nova_v2
from heatclient.v1 import client as heat_v1
from saharaclient.api import client as sahara_v2

'''
Authentication and Session Setup
'''
auth = v2.Password(auth_url = os.environ['OS_AUTH_URL'],
                   username = os.environ['OS_USERNAME'],
                   password = os.environ['OS_PASSWORD'],
                   tenant_id = os.environ['OS_TENANT_ID'])

sess = ksc_session.Session(auth=auth)

'''
Set up our connections for various services and share the session.
'''
ks = keystone_v3.Client(session=sess)
nova = nova_v2.Client(session=sess)

'''
Heat requires a service_type to be passed or it fails to authenticate.
'''
heat = heat_v1.Client(session=sess, service_type='orchestration')
sahara = sahara_v2.Client(session=sess)

'''
Just a JSON pretty-printer
'''
pp = pprint.PrettyPrinter(indent=4)


def list_users():
    '''
    Get a list of users from the keystone service endpoint.
    '''
    users = ks.users.list()
    print pp.pprint(users)


def list_instances():
    '''
    Get a list of instances from the nova service endpoint.
    '''
    instances = nova.servers.list()
    print pp.pprint(instances)


def list_plugins():
    '''
    Get a list of plugins from the sahara service endpoint.
    '''
    plugins = sahara.plugins.list()
    print pp.pprint(plugins)


def list_heat_services():
    '''
    Get a list of services from the heat/orchestration service endpoint.
    '''
    services = heat.services.list()
    print pp.pprint(services)
