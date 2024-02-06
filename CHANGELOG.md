## Unreleased (dd/mm/yyyy)

### Fixes
- O2V-226: fix vm network information parsing for onapp cp < 6.4
- O2V-228: use management network for vinfra command, implement jump host functionality to
           migration network
    - requires additional config: cp_ip_internal = xx.xx.xx.xx to be assign to vhicontroller
      node storage network ip
- O2V-230: fix incorect bash syntax on vm shut down
- O2V-232: trucate vnc passwords that are too long

## v1.1.1 (15/12/2023)

### Fixes
- O2V-220: fix vm network information parsing for onapp cp < 6.3

## v1.1.0 (15/11/2023)

### Feature

- O2V-185: Implement progress bar for long running operation
- O2V-218: refactor flavor flags
- O2V-186: Implement cli to initialize config

### Fixes
- O2V-215: Stop migrating suspended vm
- O2V-216: Fix broken migrate multiple vm in 1 single command
- O2V-219: Fix vm not handled properly if vm id is wrong
- O2V-173: setting migration_network_id with invalid value will cause migration to fail prematurely

## v1.0.3 (24/10/2023)

### Feature

- O2V-177: enable disk deletion on vm termination
- O2V-199: add option to enable cpu & ram hot plug on `migrate`
- O2V-200: Add new custom flavor flag for new vm in vhi

### Fixes

- O2V-192: Fix domain_id and vinfra_domain in config
- O2V-194: Continue migration when vm on vhi side has no IPS
- O2V-176: Remove temp files after it is copied to target vm
- O2V-205: Fix image conversion for cold migrate post VHI 6.0.0
- O2V-206: Fix error handling when quota data is not parseable
- 02V-208: Fix vinfra output parsing to handle json arrays
- O2V-210: Fix unsafe virsh destroy operation on live migrate
- O2V-207: Fix error handling when vm has no primary ip
- O2V-193: Fix vm gets migrated even user parameter is supplied wrongly

## v1.0.2 (23/08/2023)

### Feature

- O2V-156: Hide сredentials in log files
- O2V-180: Default VHI security group rules for secondary interface after migration

### Fixes

- O2V-113: fix migration results in json decode error
- O2V-171: adding option to migrate with just `--vm` parameter
- O2V-174: Fix linux cold migration grub install send-expect sequence
- O2V-146: Fix index error when multiple migrations are running
- O2V-115: Add ip range check to fix issue with networks with same subnet having different ip range
- O2V-170: Fix unexpected host key prompt
- O2V-168: Fix error handling in VHI vm creation
- O2V-159: Preserve Windows VM hostname
- O2V-175: Skip migration on onapp vm marked as VIP and fix error handling when migrating existing vm in VHI
- O2V-172: Fix error handling and pre-checks for migration with placement
- 02V-184: Fix json loads error when creating new network interface

## v1.0.1 (30/06/2023)

### Feature

- O2V-151: Adding `--storage-policy` parameter to `migrate` command

### Fixes

- O2V-148: Fix VM migrations with multiple disks and modified disk vm number
- O2V-154: improving network api calls for onapp 6.0

## v1.0.0 (20/06/2023)

- First versioned release of `onapp2vhi`
