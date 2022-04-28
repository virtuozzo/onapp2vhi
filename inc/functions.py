import collections
import shlex,subprocess
import os
import sys

plug_path=os.getcwd()
sys.path.append(plug_path)

from o2v_config import *

 ######################
##-----FUNCTION-------##
##-----run_command-------##
 ######################
def run_command(CMD,verbose=1,interactive=1):

   if verbose >= 1 and verbose < 8:
      print( "Running: " + CMD )

   elif verbose >= 8:
      print( "-----")
      print( "Running: " + CMD )
      print( "---")

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
      exit_code = subprocess.call(CMD,shell=True)

   if verbose >= 8 :
      print( "Result[" + str(exit_code) + "]: " + str(cmd_output) )
   elif verbose >= 1 and exit_code >= 1:
      print(exit_code) 

   return [exit_code, cmd_output]


