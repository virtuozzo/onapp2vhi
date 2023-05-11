@list_vm
Feature: List all VM in Onapp cloud

Scenario: List all VM
  Given I am a cloud user (uda)
  When I view the VMs in Onapp cloud using migration tool
  Then I should see the VM listed is tally with the VMs displayed in Onapp cloud

Scenario: List VM for a specified user
  Given I am a cloud user (uda)
  When I view the VMs in Onapp cloud using migration tool for user (uda)
  Then I should see the VM listed is tally with the VMs displayed in Onapp cloud

Scenario: List VM with the specified header
  Given I am a cloud user (uda)
  When I view the VMs in Onapp cloud using migration tool with following headers
  | header          |
  | identifier      |
  | hostname        |
  | memory          |
  | cpus            |
  | user_id         |
  | template_label  |
  | total_disk_size |
  Then I should see the VM listed is tally with the VMs displayed in Onapp cloud
  And I should see the VM listed has the following headers
  | header          |
  | identifier      |
  | hostname        |
  | memory          |
  | cpus            |
  | user_id         |
  | template_label  |
  | total_disk_size |

Scenario: List VM for a specified user with specified header
  Given I am a cloud user (uda)
  When I view the VMs in Onapp cloud using migration tool for user (uda) with following headers
  | header   |
  | hostname |
  Then I should see the VM listed is tally with the VMs displayed in Onapp cloud
  And I should see the VM listed has the following headers
  | header   |
  | hostname |
