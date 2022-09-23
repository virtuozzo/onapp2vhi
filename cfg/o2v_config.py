from enum import Enum

import sys

sys.dont_write_bytecode = True


# - - - - - - - - - - - - - - -
# ONAPP API CREDENTIALS ##
class OnAppAPICredentials(Enum):
    ONAPP_CP_HOST = "69.168.239.170"
    ONAPP_CP_URL = "http://{}".format(ONAPP_CP_HOST)
    ONAPP_USER_EMAIL = ''
    ONAPP_USER_APIKEY = ''
    ONAPP_SSH_PORT_CP = 2222
    ONAPP_SSH_PORT_HV = 22
    ONAPP_HV_IP = '10.120.0.101'
# - - - - - - - - - - - - - - -


# - - - - - - - - - - - - - - -
# VHI Cloud DEFAULTS ##
class VHICLoudDefaults(Enum):
    VHI_CP_URL = 'https://cvhi.onappdev.com:8888'
    VHI_PANEL_URL = 'https://cvhi.onappdev.com:8800'
    VHI_API_PATH = '/api/v2'
    VHI_CP_IP = '10.63.0.63'
    VHI_LOGIN = 'admin'
    VHI_HV_IP = '10.63.0.64'
    VHI_NETWORK = 'public1'

    VHI_SSH_PORT = 2222
    VHI_SSH_PORT_HV = 22
    VHI_LINUX_IMAGE = 'cirros'
    VHI_WINDOWS_IMAGE = 'windows2012'
    VHI_FLAVOR = 'small'
    VHI_SG_ID = '207c9e28-abe4-48b1-b704-4b5a3c0df097'
    # VHI_PROJECT_ID = '77f1c52d31d04a82aadd07fd4ead5305'
    VHI_DOMAIN_ID = '58fa18b2cefc4bad8a52f11008dfbf72'
    VINFRA_DOMAIN = 'Migration'
    VINFRA_PROJECT = 'migproj'
    VINFRA_USER = ''
    VINFRA_PASS = ''
# - - - - - - - - - - - - - - -


# - - - - - - - - - - - - - - -
# General options
class Helper(Enum):
    SSH_OPTS = "-A -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no'"
    IMG_SPARSING = False

    SPACES = ' ' * 15
    EQUAL = '=' * 18

    # VERBOSITY_LEVEL
    VERBOSITY = 8
# - - - - - - - - - - - - - - -
