# onapp2vhi - OnApp to VHI migration

---
------
---

## Setup SSH Agent Manually
  - At OnApp side run `export SSH_AUTH_SOCK=/onapp/interface/tmp/onapp-ssh-agent.socket`
  - At OnApp side run `ssh-add -L`
    - if get some error, please restart onapp daemon:
      - `service onapp status`
      - `service onapp start`
  - Save OnApp ssh key on VHI side on all nodes.

## Setup User on VHI Side

  - Login into `vinfra` on VHI side(CP, HV1, HV2) and enter password for admin
  - Create any user that will be used for migration process on the UI side
  - Take new user login and assign new role to him: 
    - `vinfra domain user set {user_login} --assign-domain Default compute --domain Default`
      - e.g.:
      - `vinfra domain user set migration_user@onapp.test.com --assign-domain Default compute --domain=Default`
  - next step is to provide user credentials into cfg/config.cfg file
  - On VHI server do next steps:
    - set into .bashrc file:
      - `source /etc/kolla/admin-openrc.sh`
    - take an ID all your networks and do next:
      - `openstack --insecure network set --disable-port-security {network-id}`
    - after migration finished revert changes:
      - `openstack --insecure network set --enable-port-security {network-id}`


## Setup local environment
#### Please provide SSH KEYS to VHI(HV, CP) and OnApp(HV, CP, BS) from machine you are going to run migration.
  - Before running "./onapp2vhi" command please do next steps:
    - you should be in onapp2vhi project `[~/onapp2vhi] $ `
    - RUN `yum -y install python3-pip`
    - RUN `pip3 –V` (NOTE: you should see pip version ___pip 20.3.4 from /migrations/.venv/lib/python2.7/site-packages/pip (python 2.7)___)
    - RUN `/usr/bin/pip3 install --upgrade pip`
    - RUN `pip3 install virtualenv`
  - NOTE: path may be different, please find where python3 is located (`which python2`)
    - RUN `virtualenv -p /usr/bin/python3 .venv`
    - RUN `source .venv/bin/activate`
    - RUN `pip install --upgrade pip`
    - inside virtual env (you should see in console "(.venv) root@root #"):
      - RUN `pip install -r requirements.txt`
  - Please provide credentials related to OnApp and VHI clouds in the file __cfg/config.cfg__
    - `vi ./cfg/config.cfg`
    - save file
  - Copy files into project root dir:
    - `vz-guest-tools-win.tar`
    - `CloudbaseInitSetup_Stable_x64.msi`
  - run next commands under `onapp` user:
    - `su - onapp`
    - `export SSH_AUTH_SOCK=/onapp/interface/tmp/onapp-ssh-agent.socket`
    - `echo "export SSH_AUTH_SOCK=/onapp/interface/tmp/onapp-ssh-agent.socket" >> /home/onapp/.bashrc `
  * You have installed separate __python 3 virtual environment__ that will not affect global python requirements.
  * You have installed all needed packages and libraries into our virtual environment. 
  * You have provided credentials to access our clouds.

---
---

## Running ./onapp2vhi examples:
    
    Please make sure you run script in onapp2vhi project FOLDER and using virtual environment:
    (.venv) [root@yourcp ~/onapp2vhi_project]# 
  - List all possible migration tool commands

    ```
    ./onapp2vhi --help
    OR
    ./onapp2vhi --h
    OR
    ./onapp2vhi help
    OR
    ./onapp2vhi man
    ```
---
  - ### Get all Virtual servers:
    ```
    ./onapp2vhi list_onapp_vms
    ```
    
  * By specifying "_find=_" or "_props=_" parameter to get what you want:
    * command will show you all VM's related to user with ID=7
      ```
      ./onapp2vhi list_onapp_vms --find="user_id=7"
      ```
    * command will show you all VM's related to user with ID=7 and columns you specified in "vals":
      ```
      ./onapp2vhi list_onapp_vms --find="user_id=7" --props=identifier,hostname,memory,cpus,user_id,template_label,total_disk_size
      ./onapp2vhi list_onapp_vms --find="identifier=lidqtfwggohyzk" --props=identifier,hostname,memory,cpus,user_id,template_label,total_disk_size
      ```
---
  - ### Get all Users:
    - ./onapp2vhi list-onapp-vms
    - the same logic is using for users:
      - command will show you only user with id=7, login=admin or email=admin@example.com
          ```
          ./onapp2vhi list_onapp_users --find="id=7" 
        OR
          ./onapp2vhi list_onapp_users --find="login=admin"
        OR 
          ./onapp2vhi list_onapp_users --find="email=admin@example.com" 
          ```
        * command will show you all VM's related to user with ID=7 and columns you specified in "vals":
          ```
          ./onapp2vhi list_onapp_users --find="login=admin" --props=id,email,login,roles,first_name,last_name
          ```
---
  - ### User migration:
    - When you decided which user should migrate, run one of next command (depends on input property):
      ```
      ./onapp2vhi user-migrate --idn=7
      OR
      ./onapp2vhi user-migrate --login=rgolovko
      OR
      ./onapp2vhi user-migrate --email=roman.holovko@virtuozzo.com
      ```
    - User has been migrated, on VHI side for user created:
      - project
      - user
      - migrated ssh keys (if he had in OnApp)
      - file with user login and password saved into /migrated_users/user_7.log
---
  - ### Linux based VM's:
    - First step is to install bootloader into VM on OnApp side:
      ```
      ./onapp2vhi install_bootloader --vm=lidqtfwggohyzk
      OR
      ./onapp2vhi install_bootloader-offline --vm=lidqtfwggohyzk
      ```
    - Then you can migrate that VM:
      ```
      ./onapp2vhi live_migrate --vm=lidqtfwggohyzk
      ```
---
  - ### Windows based VM's:
    - First step is to install bootloader into VM on OnApp side:
        ```
        ./onapp2vhi install_win_drivers --vm-identifier=qsykamkqqlpjbd
      OR
        ./onapp2vhi install_win_drivers_offline --vm-identifier=qsykamkqqlpjbd
        ```
    - Then you can migrate that VM:
      ```
      ./onapp2vhi live_migrate --vm=lidqtfwggohyzk
      ```
---
  - ### Run whole migration process:
    - Just type command:
        ```
        ./onapp2vhi migrate-all
      ```
    - If you want to migrate only one user and his VM's:
      ```
      ./onapp2vhi migrate-all --user=7
      ```
    - After script finished, please take a look in logs file:
      ```
      ~/onapp2vhi/migration_logs/
      ```
---
  - ### Deactivate environment:
    - RUN in terminal `deactivate`
---

   - ### Logs on VHI side:
     - Run command `rm -f ~/.vinfra/backend-api.svc.vstoragedomain/*`

---



