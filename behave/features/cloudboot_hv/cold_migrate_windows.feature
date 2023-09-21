@migrate_vm
@cold_migration
@windows
@cloudboothv
Feature: Cold migration for Windows VM

Scenario: Cold migration without user's SSH key
  Given I am a cloud user (ultron)
  When I create a virtual machine (windows-vm-without-startup-cloudboot)
  Then CP API (create) should return status code 201
  And I wait for 10 minutes
  And the virtual machine (windows-vm-without-startup-cloudboot) is built successfully

  When I migrate the virtual machine (windows-vm-without-startup-cloudboot)
  Then I wait for 10 seconds
  And I should see the virtual machine is SHUTOFF in VHI portal
  And its CPU, RAM and storage are correct

Scenario: Cold migration with user's SSH key
  Given I am a cloud user (uda)
  When I create a virtual machine (windows-vm-without-startup-cloudboot)
  Then CP API (create) should return status code 201
  And I wait for 10 minutes
  And the virtual machine (windows-vm-without-startup-cloudboot) is built successfully

  # To test for new migrated user, we delete the existing user account
  When I delete the existing user account (uda) from the VHI portal
  And I set the logging path (uda-log)
  And I migrate the virtual machine (windows-vm-without-startup-cloudboot)
  Then I wait for 10 seconds
  And I should see the virtual machine is SHUTOFF in VHI portal
  And its CPU, RAM and storage are correct
  And the log is seen in logging path (uda-log)

@placement
Scenario: Cold migration with user's SSH key with storage policy and placement specified
  Given I am a cloud user (uda)
  When I create a storage policy (behave-storage-policy) in VHI portal with following details
  | tier | replicas | failure domain |
  | 0    | 3        | 1              |
  And I assign the storage policy (behave-storage-policy) with 100G to the project
  And I create a placement (behave-soft-placement) in VHI portal with following details
  | nodes |
  | cpvhi |
  And I assign the placement (behave-soft-placement) with 100 placement to the project
  And I create a virtual machine (windows-vm-without-startup-cloudboot)
  Then CP API (create) should return status code 201
  And I wait for 10 minutes
  And the virtual machine (windows-vm-without-startup-cloudboot) is built successfully

  When I migrate the virtual machine (windows-vm-without-startup-cloudboot) with following details
  | storage policy        | placement             |
  | behave-storage-policy | behave-soft-placement |
  Then I wait for 10 seconds
  And I should see the virtual machine is SHUTOFF in VHI portal
  And its CPU, RAM and storage are correct
  And its volume is using the correct storage policy (behave-storage-policy)
  And the vm is placed in the corrent placement (behave-soft-placement)

@network
Scenario: Cold migration with user's SSH key with second network interface (IPv4 and IPv6)
  Given I am a cloud user (uda)
  When I create a network (behave-network-ipv4-ipv6)
  Then CP API (create) should return status code 201

  When I add a new ip net (behave-ip-net-ipv4) to network (behave-network-ipv4-ipv6)
  Then CP API (create) should return status code 201

  When I add a new ip net (behave-ip-net-ipv6) to network (behave-network-ipv4-ipv6)
  Then CP API (create) should return status code 201

  When I add the network join (behave-network-join-997) from network (behave-network-ipv4-ipv6) to the compute zone (CloudBoot Compute Zone)
  Then CP API (create) should return status code 201

  When I create a virtual machine (windows-vm-without-startup-cloudboot)
  Then CP API (create) should return status code 201
  And I wait for 10 minutes
  And the virtual machine (windows-vm-without-startup-cloudboot) is built successfully

  When I add a network interface (behave-network-interface-ipv4-ipv6) with network join (behave-network-join-997) at compute zone (CloudBoot Compute Zone) to the virtual machine (windows-vm-without-startup-cloudboot)
  Then CP API (create) should return status code 201

  When I add an IP address (behave-ip-net-ipv4) from network (behave-network-ipv4-ipv6) to the network interface (behave-network-interface-ipv4-ipv6) on virtual machine (windows-vm-without-startup-cloudboot)
  Then CP API (create) should return status code 201
  
  When I add an IP address (behave-ip-net-ipv6) from network (behave-network-ipv4-ipv6) to the network interface (behave-network-interface-ipv4-ipv6) on virtual machine (windows-vm-without-startup-cloudboot)
  Then CP API (create) should return status code 201

  When I reboot the virtual machine (windows-vm-without-startup-cloudboot) in Onapp cloud
  Then CP API (reboot) should return status code 201
  And I wait for 90 seconds

  When I shutdown the virtual machine (windows-vm-without-startup-cloudboot) in Onapp cloud
  Then CP API (shutdown) should return status code 201
  And I wait for 90 seconds

  When I migrate the virtual machine (windows-vm-without-startup-cloudboot)
  Then I wait for 10 seconds
  And I should see the virtual machine is SHUTOFF in VHI portal
  And its CPU, RAM and storage are correct