import sys
sys.dont_write_bytecode = True

#-VERBOSITY_LEVEL-
VERBOSITY = 8

#
## ONAPP API CREDENTIALS ##
ONAPP_CP_HOST = "cpinv.onappdev.com"
ONAPP_CP_URL = "https://{}".format(ONAPP_CP_HOST)
ONAPP_USER_EMAIL = 'admin@example.com'
ONAPP_USER_APIKEY = '279041cc2507e99f54e526007b9a2c7f536c4cdc'
ONAPP_SSH_PORT = 22
ONAPP_HV_IP = '10.63.0.5'
#
#
## VHI Cloud DEFAULTS ##
VHI_CP_URL = 'https://cvhi.onappdev.com:8888'
VHI_CP_IP = '10.63.0.63'

VHI_HV_IP = '10.63.0.64'

VHI_SSH_PORT = 2222
VHI_LINUX_IMAGE = 'cirros'
VHI_WINDOWS_IMAGE = 'windows2012'
VHI_FLAVOR = 'small'
VHI_SG_ID = '207c9e28-abe4-48b1-b704-4b5a3c0df097'
#
## General options
SSH_OPTS = "-o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no'"
IMG_SPARSING = False



