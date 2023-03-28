import os
import click

from inc.onapp_helpers import list_onapp_users as list_onapp_users_impl
from inc.onapp_helpers import list_onapp_vms as list_onapp_vms_impl
from inc.vhi_helpers import Vhi
from onapp2vhi.ops.cold_migrate import vm_cold_migrate
from onapp2vhi.ops.install_bootloader import vm_install_bootloader
from onapp2vhi.ops.install_bootloader_offline import vm_install_bootloader_offline
from onapp2vhi.ops.install_win_drivers import vm_install_win_drivers
from onapp2vhi.ops.install_win_drivers_offline import vm_install_win_drivers_offline
from onapp2vhi.ops.user_migrate import user_migrate_impl
from onapp2vhi.ops.live_migrate import vm_live_migrate
from onapp2vhi.ops.template_migrate import vm_template_migrate
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
@click.option('--vdom', '--vhi-domain', default='', help="VHI Domain.")
@click.option('--vproj', '--vhi-project', default='', help="VHI Project.")
@click.option('--idn', '--vm', '--identifier', '--vm-identifier', default='', help="OnApp VM identifier.")
@click.option('--network', default='', help="Set network id")
def cold_migrate(vdom='', vproj='', idn='', network='', vhi_obj=''):
    vm_cold_migrate(vdom=vdom,
                    vproj=vproj,
                    idn=idn,
                    network=network,
                    vhi_obj=vhi_obj)


@run.command()
def create_service_user():
    vhi = Vhi()
    vhi.create_service_user()


@run.command()
@click.option('--idn', '--vm', '--identifier', '--vm-identifier', default='', help="OnApp VM identifier.")
def install_bootloader(idn=''):
    vm_install_bootloader(idn=idn)


@run.command()
@click.option('--idn', '--vm', '--identifier', '--vm-identifier', default='', help="OnApp VM identifier.")
def install_bootloder_offline(idn=''):
    vm_install_bootloader_offline(idn=idn)


@run.command()
@click.option('--idn', '--vm', '--identifier', '--vm-identifier', default='', help="OnApp VM identifier.")
def install_win_drivers(idn=''):
    vm_install_win_drivers(idn=idn)


@run.command()
@click.option('--idn', '--vm', '--identifier', '--vm-identifier', default='', help="OnApp VM identifier.")
def install_win_drivers_offline(idn=''):
    vm_install_win_drivers_offline(idn=idn)


@run.command()
@click.option('--vdom', '--vhi-domain', default='', help="VHI Domain.")
@click.option('--vproj', '--vhi-project', default='', help="VHI Project.")
@click.option('--idn', '--vm', '--identifier', '--vm-identifier', default='', help="OnApp VM identifier.")
@click.option('--network', default='', help="Set network id")
def live_migrate(vdom='', vproj='', idn='', network='', vhi_obj=''):
    vm_live_migrate(vdom=vdom,
                    vproj=vproj,
                    idn=idn,
                    network=network,
                    vhi_obj=vhi_obj)


@run.command()
@click.option('--idn', '--tmpl', '--label', '--template-label', default='', help="OnApp template label.")
def template_migrate(idn='', vhip=''):
    vm_template_migrate(idn=idn, vhip=vhip)


@run.command()
@click.option('--idn', '--user', '--email', '--user-id', '--login', default='', help="OnApp User identifier.")
def user_migrate(idn=''):
    user_migrate_impl(idn=idn)


@run.command()
@click.option('--user', default='', help="OnApp User, VM identifier.")
@click.option('--network', default='', help="Network to be used")
@click.option('--vm', default='', help="VM to be migrated")
@click.option('--project', default='', help="Project where all objects will be migrated")
def migrate_all(user='', network='', vm='', project=''):
    migrate_all_impl(user=user, network=network, vm=vm, project=project)
