@migrate_vm
@hot_migration
@windows
@statichv
Feature: Hot migration for Windows VM

Scenario: Hot migration without user's SSH key
  Given I am a cloud user (ultron)
  When I create a virtual machine (windows-vm-with-startup-static1)
  Then CP API (create) should return status code 201
  And I wait for 10 minutes
  And the virtual machine (windows-vm-with-startup-static1) is built successfully

  When I set the logging path (ultron_log/log)
  And I migrate the virtual machine (windows-vm-with-startup-static1)
  Then I wait for 10 seconds
  And I should see the virtual machine (windows-vm-with-startup-static1) is ACTIVE in VHI portal
  And the virtual machine (windows-vm-with-startup-static1) should have correct CPU, RAM and storage
  And the log is seen in logging path (ultron_log/log)
  And I should see the hotplug is disabled in virtual machine (windows-vm-with-startup-static1)

Scenario: Hot migration with user's SSH key
  Given I am a cloud user (uda)
  When I create a virtual machine (windows-vm-with-startup-static1)
  Then CP API (create) should return status code 201
  And I wait for 10 minutes
  And the virtual machine (windows-vm-with-startup-static1) is built successfully

  # To test for new migrated user, we delete the existing user account
  When I delete the existing user account (uda) from the VHI portal
  And I migrate the virtual machine (windows-vm-with-startup-static1)
  Then I wait for 10 seconds
  And I should see the virtual machine (windows-vm-with-startup-static1) is ACTIVE in VHI portal
  And the virtual machine (windows-vm-with-startup-static1) should have correct CPU, RAM and storage
  And I should see the hotplug is disabled in virtual machine (windows-vm-with-startup-static1)

@placement
Scenario: Hot migration with user's SSH key with storage policy and placement specified
  Given I am a cloud user (uda)
  When I create a storage policy (behave-storage-policy) in VHI portal with following details
  | tier | replicas | failure domain |
  | 0    | 3        | 1              |
  And I assign the storage policy (behave-storage-policy) with 100G to the project
  And I create a placement (behave-hard-placement) in VHI portal with following details
  | nodes |
  | cpvhi |
  And I assign the placement (behave-hard-placement) with 100 placement to the project
  And I create a virtual machine (windows-vm-with-startup-static1)
  Then CP API (create) should return status code 201
  And I wait for 10 minutes
  And the virtual machine (windows-vm-with-startup-static1) is built successfully

  When I migrate the virtual machine (windows-vm-with-startup-static1) with following details
  | storage policy        | placement             | hotplug |
  | behave-storage-policy | behave-hard-placement | True    |
  Then I wait for 10 seconds
  And I should see the virtual machine (windows-vm-with-startup-static1) is ACTIVE in VHI portal
  And the virtual machine (windows-vm-with-startup-static1) should have correct CPU, RAM and storage
  And I should see the hotplug is enabled in virtual machine (windows-vm-with-startup-static1)
  And the virtual machine (windows-vm-with-startup-static1) is using the correct storage policy (behave-storage-policy) in its volume
  And the virtual machine (windows-vm-with-startup-static1) is placed in the corrent placement (behave-hard-placement)

Scenario: Hot migration with user's SSH key with storage policy and placement specified
  Given I am a cloud user (uda)
  When I create a virtual machine (windows-vm-with-startup-static1)
  Then CP API (create) should return status code 201
  And I wait for 10 minutes
  And the virtual machine (windows-vm-with-startup-static1) is built successfully

  When I migrate the virtual machine (windows-vm-with-startup-static1) with following details
  | hotplug |
  | True    |
  Then I wait for 10 seconds
  And I should see the virtual machine (windows-vm-with-startup-static1) is ACTIVE in VHI portal
  And the virtual machine (windows-vm-with-startup-static1) should have correct CPU, RAM and storage
  And I should see the hotplug is disabled in virtual machine (windows-vm-with-startup-static1)

@network
Scenario: Hot migration with user's SSH key with second network interface (IPv4)
  Given I am a cloud user (uda)
  When I create a network (behave-network-ipv4)
  Then CP API (create) should return status code 201

  When I add a new ip net (behave-ip-net-ipv4) to network (behave-network-ipv4)
  Then CP API (create) should return status code 201

  When I add the network join (behave-network-join-993) from network (behave-network-ipv4) to the compute zone (Static Compute Zone)
  Then CP API (create) should return status code 201

  When I create a virtual machine (windows-vm-with-startup-static1)
  Then CP API (create) should return status code 201
  And I wait for 10 minutes
  And the virtual machine (windows-vm-with-startup-static1) is built successfully

  When I add a network interface (behave-network-interface-ipv4) with network join (behave-network-join-993) at compute zone (Static Compute Zone) to the virtual machine (windows-vm-with-startup-static1)
  Then CP API (create) should return status code 201

  When I add an IP address (behave-ip-net-ipv4) from network (behave-network-ipv4) to the network interface (behave-network-interface-ipv4) on virtual machine (windows-vm-with-startup-static1)
  Then CP API (create) should return status code 201

  When I reboot the virtual machine (windows-vm-with-startup-static1) in Onapp cloud
  Then CP API (reboot) should return status code 201
  And I wait for 90 seconds

  When I migrate the virtual machine (windows-vm-with-startup-static1)
  Then I wait for 10 seconds
  And I should see the virtual machine (windows-vm-with-startup-static1) is ACTIVE in VHI portal
  And the virtual machine (windows-vm-with-startup-static1) should have correct CPU, RAM and storage
  And I should see the hotplug is disabled in virtual machine (windows-vm-with-startup-static1)

@network
Scenario: Hot migration with user's SSH key with second network interface (IPv6)
  Given I am a cloud user (uda)
  When I create a network (behave-network-ipv6)
  Then CP API (create) should return status code 201

  When I add a new ip net (behave-ip-net-ipv6) to network (behave-network-ipv6)
  Then CP API (create) should return status code 201

  When I add the network join (behave-network-join-994) from network (behave-network-ipv6) to the compute zone (Static Compute Zone)
  Then CP API (create) should return status code 201

  When I create a virtual machine (windows-vm-with-startup-static1)
  Then CP API (create) should return status code 201
  And I wait for 10 minutes
  And the virtual machine (windows-vm-with-startup-static1) is built successfully

  When I add a network interface (behave-network-interface-ipv6) with network join (behave-network-join-994) at compute zone (Static Compute Zone) to the virtual machine (windows-vm-with-startup-static1)
  Then CP API (create) should return status code 201

  When I add an IP address (behave-ip-net-ipv6) from network (behave-network-ipv6) to the network interface (behave-network-interface-ipv6) on virtual machine (windows-vm-with-startup-static1)
  Then CP API (create) should return status code 201

  When I reboot the virtual machine (windows-vm-with-startup-static1) in Onapp cloud
  Then CP API (reboot) should return status code 201
  And I wait for 90 seconds

  When I migrate the virtual machine (windows-vm-with-startup-static1)
  Then I wait for 10 seconds
  And I should see the virtual machine (windows-vm-with-startup-static1) is ACTIVE in VHI portal
  And the virtual machine (windows-vm-with-startup-static1) should have correct CPU, RAM and storage
  And I should see the hotplug is disabled in virtual machine (windows-vm-with-startup-static1)