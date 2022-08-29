from enum import Enum

import sys

sys.dont_write_bytecode = True


# - - - - - - - - - - - - - - -
# ONAPP API CREDENTIALS ##
class OnAppAPICredentials(Enum):
    ONAPP_CP_HOST = "cpinv.onappdev.com"
    ONAPP_CP_URL = "https://{}".format(ONAPP_CP_HOST)
    ONAPP_USER_EMAIL = 'admin@example.com'
    ONAPP_USER_APIKEY = '279041cc2507e99f54e526007b9a2c7f536c4cdc'
    ONAPP_SSH_PORT = 22
    ONAPP_HV_IP = '10.63.0.5'
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

    VHI_SSH_PORT = 2222
    VHI_LINUX_IMAGE = 'cirros'
    VHI_WINDOWS_IMAGE = 'windows2012'
    VHI_FLAVOR = 'small'
    VHI_SG_ID = '207c9e28-abe4-48b1-b704-4b5a3c0df097'
    # VHI_PROJECT_ID = '77f1c52d31d04a82aadd07fd4ead5305'
    VHI_DOMAIN_ID = '58fa18b2cefc4bad8a52f11008dfbf72'
    VINFRA_DOMAIN = 'Migration'
    VINFRA_PROJECT = 'migproj'
    VINFRA_USER = 'onapp2'
    VINFRA_PASS = '4OnApp13777'
# - - - - - - - - - - - - - - -


# - - - - - - - - - - - - - - -
# General options
class Helper(Enum):
    SSH_OPTS = "-o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no'"
    IMG_SPARSING = False

    SPACES = ' ' * 15

    # VERBOSITY_LEVEL
    VERBOSITY = 8
# - - - - - - - - - - - - - - -
