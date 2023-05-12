from enum import Enum
import sys

sys.dont_write_bytecode = True


# General options
class Helper(Enum):
    SSH_OPTS = "-A -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no'"
    SCP_OPTS = "-o 'ForwardAgent yes' -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no'"
    IMG_SPARSING = False

    SPACES = ' ' * 15
    EQUAL = '=' * 18

    # VERBOSITY_LEVEL
    VERBOSITY = 8
