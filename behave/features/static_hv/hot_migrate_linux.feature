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

@placement
Scenario: Hot migration with user's SSH key with storage policy and placement specified
  Given I am a cloud user (uda)
  When I create a storage policy (behave-storage-policy) in VHI portal with following details
  | tier | replicas | failure domain |
  | 0    | 3        | 1              |
  And I assign the storage policy (behave-storage-policy) with 100G to the project
  And I create a placement (behave-soft-placement) in VHI portal with following details
  | nodes |
  | cpvhi |
  And I assign the placement (behave-soft-placement) with 100 placement to the project
  And I create a virtual machine (linux-vm-with-startup-static)
  Then CP API (create) should return status code 201
  And I wait for 2 minutes
  And the virtual machine (linux-vm-with-startup-static) is built successfully

  When I migrate the virtual machine (linux-vm-with-startup-static) with following details
  | storage policy        | placement             |
  | behave-storage-policy | behave-soft-placement |
  Then I wait for 10 seconds
  And I should see the virtual machine is ACTIVE in VHI portal
  And its CPU, RAM and storage are correct
  And its volume is using the correct storage policy (behave-storage-policy)
  And the vm is placed in the corrent placement (behave-soft-placement)

@network
Scenario: Hot migration with user's SSH key with second network interface (IPv4)
  Given I am a cloud user (uda)
  When I create a network (behave-network-ipv4)
  Then CP API (create) should return status code 201

  When I add a new ip net (behave-ip-net-ipv4) to network (behave-network-ipv4)
  Then CP API (create) should return status code 201

  When I add the network join (behave-network-join-993) from network (behave-network-ipv4) to the compute zone (Static Compute Zone)
  Then CP API (create) should return status code 201

  When I create a virtual machine (linux-vm-with-startup-static)
  Then CP API (create) should return status code 201
  And I wait for 2 minutes
  And the virtual machine (linux-vm-with-startup-static) is built successfully

  When I add a network interface (behave-network-interface-ipv4) with network join (behave-network-join-993) at compute zone (Static Compute Zone) to the virtual machine (linux-vm-with-startup-static)
  Then CP API (create) should return status code 201

  When I add an IP address (behave-ip-net-ipv4) from network (behave-network-ipv4) to the network interface (behave-network-interface-ipv4) on virtual machine (linux-vm-with-startup-static)
  Then CP API (create) should return status code 201

  When I reboot the virtual machine (linux-vm-with-startup-static) in Onapp cloud
  Then CP API (reboot) should return status code 201
  And I wait for 60 seconds

  When I migrate the virtual machine (linux-vm-with-startup-static)
  Then I wait for 10 seconds
  And I should see the virtual machine is ACTIVE in VHI portal
  And its CPU, RAM and storage are correct

@network
Scenario: Hot migration with user's SSH key with second network interface (IPv4 and IPv6)
  Given I am a cloud user (uda)
  When I create a network (behave-network-ipv4-ipv6)
  Then CP API (create) should return status code 201

  When I add a new ip net (behave-ip-net-ipv4) to network (behave-network-ipv4-ipv6)
  Then CP API (create) should return status code 201

  When I add a new ip net (behave-ip-net-ipv6) to network (behave-network-ipv4-ipv6)
  Then CP API (create) should return status code 201

  When I add the network join (behave-network-join-997) from network (behave-network-ipv4-ipv6) to the compute zone (Static Compute Zone)
  Then CP API (create) should return status code 201

  When I create a virtual machine (linux-vm-with-startup-static)
  Then CP API (create) should return status code 201
  And I wait for 2 minutes
  And the virtual machine (linux-vm-with-startup-static) is built successfully

  When I add a network interface (behave-network-interface-ipv4-ipv6) with network join (behave-network-join-997) at compute zone (Static Compute Zone) to the virtual machine (linux-vm-with-startup-static)
  Then CP API (create) should return status code 201

  When I add an IP address (behave-ip-net-ipv4) from network (behave-network-ipv4-ipv6) to the network interface (behave-network-interface-ipv4-ipv6) on virtual machine (linux-vm-with-startup-static)
  Then CP API (create) should return status code 201
  
  When I add an IP address (behave-ip-net-ipv6) from network (behave-network-ipv4-ipv6) to the network interface (behave-network-interface-ipv4-ipv6) on virtual machine (linux-vm-with-startup-static)
  Then CP API (create) should return status code 201

  When I reboot the virtual machine (linux-vm-with-startup-static) in Onapp cloud
  Then CP API (reboot) should return status code 201
  And I wait for 60 seconds

  When I migrate the virtual machine (linux-vm-with-startup-static)
  Then I wait for 10 seconds
  And I should see the virtual machine is ACTIVE in VHI portal
  And its CPU, RAM and storage are correct