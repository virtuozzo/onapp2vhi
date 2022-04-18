#!/usr/bin/env python

import os
import sys
import click
from click_default_group import DefaultGroup

plug_path=os.getcwd()
#print plug_path
sys.path.append(plug_path)
sys.path.append(plug_path+'/cfg')
sys.path.append(plug_path+'/inc')

from o2v_config import *
from functions import *
from onapp_helpers import *

verbosity=8

@click.group(cls=DefaultGroup, default='vms', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass

@click.command()
@click.option('--vals','--values','--select','--vm-identifier', default='', help="Select specific params with --select=a,b,c option.")
@click.option('--by','--where','--where-arg', default='', help="Select by specific params with --where='id=13' option.")
#click.argument('name',default='') - not used
def vms(vals='',by=''):
    #print("vals: "+ vals, "by: "+ by)
    URL = 'https://cpinv.onappdev.com/virtual_machines.json'
    list_onapp_vms(vals,by,URL)

cli.add_command(vms)


