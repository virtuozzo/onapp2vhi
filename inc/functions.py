import collections
import shlex, subprocess
import os
import sys

plug_path = os.getcwd()
sys.path.append(plug_path)

from o2v_config import *
from logger import OnAppVHILogger

logs = OnAppVHILogger()

######################
##-----FUNCTION-------##
##-----run_command-------##
######################
def run_command(CMD, verbose=1, interactive=1, comment=''):
    if verbose >= 1 and verbose < 8:
        if verbose >= 5 and comment != '':
            logs.info("-----")
            logs.info(comment)
        logs.info("----")
        logs.info("Running: " + CMD)
        if verbose >= 5 and comment != '':
            logs.info("---")

    elif verbose >= 8:
        if comment != '':
            logs.info(str(comment).strip())
        logs.info("----")
        logs.info("Running: " + CMD)
        logs.info("---")

    if interactive <= 0:
        cmd_process = subprocess.Popen(
            CMD,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        cmd_output = cmd_process.communicate()[0]
        exit_code = cmd_process.returncode
    else:
        cmd_output = ''
        exit_code = subprocess.call(CMD, shell=True)

    if verbose >= 8:
        logs.info("Result[" + str(exit_code) + "]: " + str(cmd_output))
    elif verbose >= 1 and exit_code >= 1:
        logs.info(exit_code)

    return [exit_code, cmd_output]
