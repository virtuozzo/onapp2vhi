@migrate_vm
@hot_migration
@windows
Feature: Hot migration for Windows VM

Scenario: Hot migration without user's SSH key
  Given I am a cloud user (ultron)
  When I create a virtual machine (windows-vm-with-startup)
  Then CP API (create) should return status code 201
  And I wait for 10 minutes
  And the virtual machine (windows-vm-with-startup) is built successfully

  When I set the logging path (ultron_log/log)
  And I migrate the virtual machine (windows-vm-with-startup)
  Then I wait for 10 seconds
  And I should see the virtual machine is ACTIVE in VHI portal
  And the log is seen in logging path (ultron_log/log)

Scenario: Hot migration with user's SSH key
  Given I am a cloud user (uda)
  When I create a virtual machine (windows-vm-with-startup)
  Then CP API (create) should return status code 201
  And I wait for 10 minutes
  And the virtual machine (windows-vm-with-startup) is built successfully

  # To test for new migrated user, we delete the existing user account
  When I delete the existing user account (uda) from the VHI portal
  And I migrate the virtual machine (windows-vm-with-startup)
  Then I wait for 10 seconds
  And I should see the virtual machine is ACTIVE in VHI portal