#!/usr/bin/env python2

import os
import sys
import click
from click_default_group import DefaultGroup

plug_path = os.getcwd()
sys.path.append(plug_path)
sys.path.append(plug_path + '/cfg')
sys.path.append(plug_path + '/inc')

from o2v_config import *
from functions import *
from onapp_helpers import *


@click.group(cls=DefaultGroup, default='users', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
@click.option('--vals', '--values', '--select', '--vm-identifier', default='',
              help="Select specific params with --select=a,b,c option.")
@click.option('--by', '--where', '--where-arg', default='',
              help="Select by specific params with --where='id=13' option.")
@click.option('--verb', '-v', '--v', '--verbosity', default='', help="Verbolity level of values between 0 and 8")
# click.argument('name',default='') - not used
def users(vals='', by='', verb=''):
    if verb == '': verb = "0"
    if not str(verb).isdigit():
        logs.info("Effor: '--verbosity' parameter should be a number")
        exit(11)
    if int(verb) < 0 or int(verb) > 8:
        logs.info("Effor: '--verbosity' parameter should be a number between 0 and 8")
        exit(12)
    if verb != '':
        verbosity = int(verb)
    else:
        verbosity = int(VERBOSITY)
    # logs.info("vals: "+ vals, "by: " + by)
    # logs.info("verb: " + str(verb) , "verbosity: " + str(verbosity))
    URL = 'https://cpinv.onappdev.com/users.json'
    list_onapp_users(vals, by, URL, verbosity)


cli.add_command(users)
