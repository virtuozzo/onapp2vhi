import os
import click

from onapp2vhi.inc.onapp_helpers import list_onapp_users as list_onapp_users_impl
from onapp2vhi.inc.onapp_helpers import list_onapp_vms as list_onapp_vms_impl
from onapp2vhi.inc.vhi_helpers import Vhi
from onapp2vhi.ops.migrate_all import migrate_all_impl


@click.group()
def run():
    pass


@run.command()
@click.option('--props', '--properties', '--select', '--vm-identifier', default='',
              help="Select specific params with --select=a,b,c option.")
@click.option('--find', '--where', '--where-arg', default='',
              help="Select by specific params with --where='id=13' option.")
def list_onapp_users(props='', find=''):
    list_onapp_users_impl(props=props, find=find)


@run.command()
@click.option('--props', '--properties', '--select', default='',
              help="Select specific params with --props=a,b,c option.")
@click.option('--find', '--where', '--where-arg', default='',
              help="Select by specific params with --where='id=13' option.")
def list_onapp_vms(props='', find=''):
    list_onapp_vms_impl(props=props, find=find)


@run.command()
def create_service_user():
    vhi = Vhi()
    vhi.create_service_user()


@run.command()
@click.option('--user', default='', help="OnApp User, VM identifier.")
@click.option('--network', default='', help="Network to be used")
@click.option('--vm', default='', help="VM to be migrated")
@click.option('--project', default='', help="Project where all objects will be migrated")
@click.option('--cloud_init_install', default='', help="Project where all objects will be migrated")
@click.option('--vz_guest_tools_install', default='', help="Project where all objects will be migrated")
def migrate_all(user='', network='', vm='', project='', vz_guest_tools_install='true', cloud_init_install='true'):
    migrate_all_impl(user=user,
        network=network,
        vm=vm, project=project,
        vz_guest_tools_install=vz_guest_tools_install,
        cloud_init_install=cloud_init_install)
