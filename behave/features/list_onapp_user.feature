@list_user
Feature: List all user in Onapp cloud

Scenario: List all user
  Given I am a cloud user (uda)
  When I view the users in Onapp cloud using migration tool
  Then I should see the user listed is tally with the users displayed in Onapp cloud

Scenario: List a specified user
  Given I am a cloud user (uda)
  When I view the users in Onapp cloud using migration tool for user (uda)
  Then I should see the user listed is tally with the users displayed in Onapp cloud

Scenario: List all user with the specified header
  Given I am a cloud user (uda)
  When I view the users in Onapp cloud using migration tool with following headers
  | header     |
  | id         |
  | first_name |
  | last_name  |
  | email      |
  | roles      |
  | login      |
  Then I should see the user listed is tally with the users displayed in Onapp cloud
  And I should see the user listed has the following headers
  | header     |
  | id         |
  | first_name |
  | last_name  |
  | email      |
  | roles      |
  | login      |

Scenario: List an user with the specified header
  Given I am a cloud user (uda)
  When I view the users in Onapp cloud using migration tool for user (uda) with following headers
  | header     |
  | id         |
  | first_name |
  | last_name  |
  Then I should see the user listed is tally with the users displayed in Onapp cloud
  And I should see the user listed has the following headers
  | header     |
  | id         |
  | first_name |
  | last_name  |

Scenario: List an user by using login
  Given I am a cloud user (uda)
  When I view the users in Onapp cloud using migration tool by using login (uda)
  Then I should see the user listed is tally with the users displayed in Onapp cloud

Scenario: List an user by using email
  Given I am a cloud user (uda)
  When I view the users in Onapp cloud using migration tool by using email (uda-behave@virtuozzo.com)
  Then I should see the user listed is tally with the users displayed in Onapp cloud