@create_vm
Feature: VM creation in Onapp cloud

# to ensure the vm is deleted before we create a new one
Scenario: Delete the VMs
  Given I am a cloud user (uda)
  When I delete the virtual machine (windows-vm)
  Then CP API (delete) should return status code 204

  When I delete the virtual machine (linux-vm)
  Then I wait for 1 minute
  And CP API (delete) should return status code 204

Scenario: Create a Linux VM
  Given I am a cloud user (uda)
  When I create a virtual machine (linux-vm)
  Then CP API (create) should return status code 201
  And I wait for 2 minutes
  Then the virtual machine (linux-vm) is built successfully

Scenario: Create a Windows VM
  Given I am a cloud user (uda)
  When I create a virtual machine (windows-vm)
  Then CP API (create) should return status code 201
  And I wait for 10 minutes
  Then the virtual machine (window-vm) is built successfully
