@migrate_vm
@hot_migration
@linux
@statichv
Feature: Hot migration for Linux VM

Scenario: Hot migration without user's SSH key
  Given I am a cloud user (ultron)
  When I create a virtual machine (linux-vm-with-startup-static)
  Then CP API (create) should return status code 201
  And I wait for 2 minutes
  And the virtual machine (linux-vm-with-startup-static) is built successfully

  # To test for new migrated user, we delete the existing user account
  When I delete the existing user account (ultron) from the VHI portal
  And I set the logging path (ultron_log/log)
  And I migrate the virtual machine (linux-vm-with-startup-static)
  Then I wait for 10 seconds
  And I should see the virtual machine is ACTIVE in VHI portal
  And its CPU, RAM and storage are correct
  And the log is seen in logging path (ultron_log/log)

Scenario: Hot migration with user's SSH key
  Given I am a cloud user (uda)
  When I create a virtual machine (linux-vm-with-startup-static)
  Then CP API (create) should return status code 201
  And I wait for 2 minutes
  And the virtual machine (linux-vm-with-startup-static) is built successfully

  When I migrate the virtual machine (linux-vm-with-startup-static)
  Then I wait for 10 seconds
  And I should see the virtual machine is ACTIVE in VHI portal
  And its CPU, RAM and storage are correct

Scenario: Hot migration with user's SSH key with storage policy specified
  Given I am a cloud user (uda)
  When I create a storage policy (behave-storage-policy) in VHI portal with following details
  | tier | replicas | failure domain |
  | 0    | 3        | 1              |
  And I assign the storage policy (behave-storage-policy) with 100G to the project
  And I create a virtual machine (linux-vm-with-startup-static)
  Then CP API (create) should return status code 201
  And I wait for 2 minutes
  And the virtual machine (linux-vm-with-startup-static) is built successfully

  When I migrate the virtual machine (linux-vm-with-startup-static) with following details
  | storage policy        |
  | behave-storage-policy |
  Then I wait for 10 seconds
  And I should see the virtual machine is ACTIVE in VHI portal
  And its CPU, RAM and storage are correct
  And its volume is using the correct storage policy (behave-storage-policy)