#!/usr/bin/env python

import os
import sys
import click
from inc.onapp_helpers import list_onapp_vms

plug_path = os.getcwd()
sys.path.append(plug_path)
sys.path.append(plug_path + '/cfg')
sys.path.append(plug_path + '/inc')

from click_default_group import DefaultGroup
from ops import logs
from cfg.o2v_config import Helper


@click.group(cls=DefaultGroup, default='vms', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--vals', '--values', '--select', '--vm-identifier', default='',
              help="Select specific params with --select=a,b,c option.")
@click.option('--by', '--where', '--where-arg', default='',
              help="Select by specific params with --where='id=13' option.")
@click.option('--verb', '-v', '--v', '--verbosity', default='', help="Verbosity level of values between 0 and 8")
# click.argument('name',default='') - not used
def vms(vals='', by='', verb=''):
    if not verb:
        verb = "0"
    if not str(verb).isdigit():
        logs.error("'--verbosity' parameter should be a number")
        exit(11)
    if int(verb) < 0 or int(verb) > 8:
        logs.error("'--verbosity' parameter should be a number between 0 and 8")
        exit(12)
    if verb:
        verbosity = int(verb)
    else:
        verbosity = int(Helper.VERBOSITY.value)
    # logs.info("vals: "+ vals, "by: " + by)
    # logs.info("verb: " + str(verb) , "verbosity: " + str(verbosity))
    URL = 'https://cpinv.onappdev.com/virtual_machines.json'
    list_onapp_vms(vals, by, URL, verbosity)


cli.add_command(vms)
