@migrate_vm
@cold_migration
@windows
Feature: Cold migration for Windows VM

# to ensure the vm is deleted before we create a new one
Background: Delete VM in Onapp cloud and VHI portal

  Given I am a cloud user (ultron)
  When I delete the virtual machine (windows-vm-without-startup) in Onapp cloud
  Then I wait for 1 minute
  And CP API (delete) should return status code 204

  When I delete the virtual machine (windows-vm-without-startup) in VHI portal
  Then I wait for 30 seconds
  And the virtual machine (windows-vm-without-startup) is deleted successfully

Scenario: Cold migration without user's SSH key
  Given I am a cloud user (ultron)
  When I create a virtual machine (windows-vm-without-startup)
  Then CP API (create) should return status code 201
  And I wait for 10 minutes
  And the virtual machine (windows-vm-without-startup) is built successfully

  When I migrate the virtual machine (windows-vm-without-startup)
  Then I wait for 10 seconds
  And I should see the virtual machine is SHUTOFF in VHI portal

Scenario: Cold migration with user's SSH key
  Given I am a cloud user (uda)
  When I create a virtual machine (windows-vm-without-startup)
  Then CP API (create) should return status code 201
  And I wait for 10 minutes
  And the virtual machine (windows-vm-without-startup) is built successfully

  When I migrate the virtual machine (windows-vm-without-startup)
  Then I wait for 10 seconds
  And I should see the virtual machine is SHUTOFF in VHI portal