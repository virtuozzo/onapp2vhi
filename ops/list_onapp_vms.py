import click

from inc.onapp_helpers import list_onapp_vms
from click_default_group import DefaultGroup


@click.group(cls=DefaultGroup, default='listonappvms', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--props', '--properties', '--select', default='',
              help="Select specific params with --props=a,b,c option.")
@click.option('--find', '--where', '--where-arg', default='',
              help="Select by specific params with --where='id=13' option.")
def listonappvms(props='', find=''):
    list_onapp_vms(props=props, find=find)


cli.add_command(listonappvms)
