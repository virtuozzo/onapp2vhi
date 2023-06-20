@create_vm
Feature: VM creation in Onapp cloud

# to ensure the vm is deleted before we create a new one
Scenario: Delete the VMs
  Given I am a cloud user (uda)
  When I delete the virtual machine (windows-vm-with-startup) in Onapp cloud
  Then CP API (delete) should return status code 204

  When I delete the virtual machine (linux-vm-with-startup) in Onapp cloud
  Then I wait for 1 minute
  And CP API (delete) should return status code 204

@linux
Scenario: Create a Linux VM
  Given I am a cloud user (uda)
  When I create a virtual machine (linux-vm-with-startup)
  Then CP API (create) should return status code 201
  And I wait for 2 minutes
  Then the virtual machine (linux-vm-with-startup) is built successfully

@windows
Scenario: Create a Windows VM
  Given I am a cloud user (uda)
  When I create a virtual machine (windows-vm-with-startup)
  Then CP API (create) should return status code 201
  And I wait for 10 minutes
  Then the virtual machine (windows-vm-with-startup) is built successfully
