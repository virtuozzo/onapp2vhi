@migrate_vm
@hot_migration
@linux
@cloudboothv
Feature: Hot migration for Linux VM

Scenario: Hot migration without user's SSH key
  Given I am a cloud user (ultron)
  When I create a virtual machine (linux-vm-with-startup-cloudboot1)
  Then CP API (create) should return status code 201
  And I wait for 2 minutes
  And the virtual machine (linux-vm-with-startup-cloudboot1) is built successfully

  # To test for new migrated user, we delete the existing user account
  When I delete the existing user account (ultron) from the VHI portal
  And I set the logging path (ultron_log/log)
  And I migrate the virtual machine (linux-vm-with-startup-cloudboot1)
  Then I wait for 10 seconds
  And I should see the virtual machine (linux-vm-with-startup-cloudboot1) is ACTIVE in VHI portal
  And the virtual machine (linux-vm-with-startup-cloudboot1) should have correct CPU, RAM and storage
  And the log is seen in logging path (ultron_log/log)

Scenario: Hot migration with user's SSH key
  Given I am a cloud user (uda)
  When I create a virtual machine (linux-vm-with-startup-cloudboot1)
  Then CP API (create) should return status code 201
  And I wait for 2 minutes
  And the virtual machine (linux-vm-with-startup-cloudboot1) is built successfully

  When I migrate the virtual machine (linux-vm-with-startup-cloudboot1)
  Then I wait for 10 seconds
  And I should see the virtual machine (linux-vm-with-startup-cloudboot1) is ACTIVE in VHI portal
  And the virtual machine (linux-vm-with-startup-cloudboot1) should have correct CPU, RAM and storage

@placement
@storage_policy
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
  And I create a virtual machine (linux-vm-with-startup-cloudboot1)
  Then CP API (create) should return status code 201
  And I wait for 2 minutes
  And the virtual machine (linux-vm-with-startup-cloudboot1) is built successfully

  When I migrate the virtual machine (linux-vm-with-startup-cloudboot1) with following details
  | storage policy        | placement             |
  | behave-storage-policy | behave-hard-placement |
  Then I wait for 10 seconds
  And I should see the virtual machine (linux-vm-with-startup-cloudboot1) is ACTIVE in VHI portal
  And the virtual machine (linux-vm-with-startup-cloudboot1) should have correct CPU, RAM and storage
  And the virtual machine (linux-vm-with-startup-cloudboot1) is using the correct storage policy (behave-storage-policy) in its volume
  And the virtual machine (linux-vm-with-startup-cloudboot1) is placed in the corrent placement (behave-hard-placement)

@network
Scenario: Hot migration with user's SSH key with second network interface (IPv6)
  Given I am a cloud user (uda)
  When I create a network (behave-network-ipv6)
  Then CP API (create) should return status code 201

  When I add a new ip net (behave-ip-net-ipv6) to network (behave-network-ipv6)
  Then CP API (create) should return status code 201

  When I add the network join (behave-network-join-994) from network (behave-network-ipv6) to the compute zone (CloudBoot Compute Zone)
  Then CP API (create) should return status code 201

  When I create a virtual machine (linux-vm-with-startup-cloudboot1)
  Then CP API (create) should return status code 201
  And I wait for 2 minutes
  And the virtual machine (linux-vm-with-startup-cloudboot1) is built successfully

  When I add a network interface (behave-network-interface-ipv6) with network join (behave-network-join-994) at compute zone (CloudBoot Compute Zone) to the virtual machine (linux-vm-with-startup-cloudboot1)
  Then CP API (create) should return status code 201

  When I add an IP address (behave-ip-net-ipv6) from network (behave-network-ipv6) to the network interface (behave-network-interface-ipv6) on virtual machine (linux-vm-with-startup-cloudboot1)
  Then CP API (create) should return status code 201

  When I reboot the virtual machine (linux-vm-with-startup-cloudboot1) in Onapp cloud
  Then CP API (reboot) should return status code 201
  And I wait for 90 seconds

  When I migrate the virtual machine (linux-vm-with-startup-cloudboot1)
  Then I wait for 10 seconds
  And I should see the virtual machine (linux-vm-with-startup-cloudboot1) is ACTIVE in VHI portal
  And the virtual machine (linux-vm-with-startup-cloudboot1) should have correct CPU, RAM and storage

@package_installation
Scenario: HOT migration without user's SSH key with guest-tools and cloud-init disabled
  Given I am a cloud user (ultron)
  When I create a virtual machine (linux-vm-with-startup-cloudboot1)
  Then CP API (create) should return status code 201
  And I wait for 2 minutes
  And the virtual machine (linux-vm-with-startup-cloudboot1) is built successfully

  # To test for new migrated user, we delete the existing user account
  When I delete the existing user account (ultron) from the VHI portal
  And I migrate the virtual machine (linux-vm-with-startup-cloudboot1) with following details
  | vz guest tools install | cloud init install |
  | false                  | false              |
  Then I wait for 10 seconds
  And I should see the virtual machine (linux-vm-without-startup-cloudboot1) is ACTIVE in VHI portal
  And the virtual machine (linux-vm-with-startup-cloudboot1) should have correct CPU, RAM and storage
  And the virtual machine (linux-vm-with-startup-cloudboot1) should not have guest-tools installed
  And the virtual machine (linux-vm-with-startup-cloudboot1) should not have cloud-init installed