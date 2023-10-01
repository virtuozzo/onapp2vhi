## Unreleased (06/10/2023)

### Feature

- O2V-185: Implement progress bar for long running operation

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

## v1.0.1 (30/06/2023)

### Feature

- O2V-151: Adding `--storage-policy` parameter to `migrate` command

### Fixes

- O2V-148: Fix VM migrations with multiple disks and modified disk vm number
- O2V-154: improving network api calls for onapp 6.0

## v1.0.0 (20/06/2023)

- First versioned release of `onapp2vhi`
