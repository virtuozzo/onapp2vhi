@migrate_vm
@cold_migration
@linux
Feature: Cold migration for Linux VM

Scenario: Cold migration without user's SSH key
  Given I am a cloud user (ultron)
  When I create a virtual machine (linux-vm-without-startup)
  Then CP API (create) should return status code 201
  And I wait for 2 minutes
  And the virtual machine (linux-vm-without-startup) is built successfully

  # To test for new migrated user, we delete the existing user account
  When I delete the existing user account (ultron) from the VHI portal
  And I migrate the virtual machine (linux-vm-without-startup)
  Then I wait for 10 seconds
  And I should see the virtual machine is SHUTOFF in VHI portal

Scenario: Cold migration with user's SSH key
  Given I am a cloud user (uda)
  When I create a virtual machine (linux-vm-without-startup)
  Then CP API (create) should return status code 201
  And I wait for 2 minutes
  And the virtual machine (linux-vm-without-startup) is built successfully

  When I migrate the virtual machine (linux-vm-without-startup)
  Then I wait for 10 seconds
  And I should see the virtual machine is SHUTOFF in VHI portal