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

## Setup local environment

#### Please provide SSH KEYS to VHI(HV, CP) and OnApp(HV, CP, BS) from machine you are going to run migration.

- Before running "./onapp2vhi" command please do next steps:
    - you should be in onapp2vhi project `[~/onapp2vhi] $ `
    - RUN `yum -y install python3-pip`
    - RUN `pip3 –V` or `pip -V` (NOTE: you should see pip version ___pip 21.3.1 from
      /home/onapp/onapp2vhi/.venv3/lib64/python3.6/site-packages/pip (python 3.6)___)
    - RUN `/usr/bin/pip3 install --upgrade pip`
    - RUN `pip3 install virtualenv`
- NOTE: path may be different, please find where python3 is located (`which python3`)
    - RUN `virtualenv -p /usr/bin/python3 .venv`
    - RUN `source .venv/bin/activate`
    - RUN `pip install --upgrade pip`
    - inside virtual env (you should see in console "(.venv) root@root #"):
        - RUN `pip install -r requirements.txt`
- Please provide credentials related to OnApp and VHI clouds in the file __cfg/config.cfg__
    - `vi ./cfg/config.cfg`
    - save file
- Download files:
  - http://downloads.repo.onapp.com/vz-guest-tools-lin.tar
  - http://downloads.repo.onapp.com/vz-guest-tools-win.tar
  - https://cloudbase.it/downloads/CloudbaseInitSetup_Stable_x64.msi
  - Copy into `project/scripts/` folder
    - `/scripts/vz-guest-tools-lin.tar`
    - `/scripts/vz-guest-tools-win.tar`
    - `/scripts/CloudbaseInitSetup_Stable_x64.msi`

- run next commands under `onapp` user:
    - `su - onapp`
    - `export SSH_AUTH_SOCK=/onapp/interface/tmp/onapp-ssh-agent.socket`
    - `echo "export SSH_AUTH_SOCK=/onapp/interface/tmp/onapp-ssh-agent.socket" >> /home/onapp/.bashrc `

* You have installed separate __python 3 virtual environment__ that will not affect global python requirements.
* You have installed all needed packages and libraries into our virtual environment.
* You have provided credentials to access our clouds.

## Setup User on VHI Side

- run virtual env [~/onapp2vhi]# source .venv/bin/activate
    - run next command: `(.venv)[~/onapp2vhi]# ./onapp2vhi create_service_user`
    - user for migrations will be created and saved into cfg/config.cfg file with credentials
- On VHI server do next steps:
    - set into .bashrc file:
        - `source /etc/kolla/admin-openrc.sh`
    - take an ID all your networks and do next:
        - `openstack --insecure network set --disable-port-security network_id`
    - after migration finished revert changes:
        - `openstack --insecure network set --enable-port-security network_id`

---
---

## Running ./onapp2vhi examples:
  * Please make sure you run script in onapp2vhi project FOLDER and using virtual environment:
    ```
    (.venv) [onapp@yourcp ~/onapp2vhi_project]# 
    ```
  * If you want see logs in DEBUG mode, please create environmental variable:

    ```
    (.venv) [onapp@yourcp ~/onapp2vhi_project]# export loglevel=debug
    ```

- `onapp2vhi` HELP

  ```
  ./onapp2vhi --help
  OR
  ./onapp2vhi --h
  OR
  ./onapp2vhi help
  OR
  ./onapp2vhi man
  ```

- Currently, migration tool provides next commands:
  * **Providers**:
    * `create_service_user` - command will create special user under the hood for migration and save his credentials into config file
    * `list_onapp_users` - get and show all user at OnApp cloud
    * `list_onapp_vms` - get and show all virtual machines at OnApp cloud
    * `migrate` - entry point to start migration

---

- ### Show all Virtual Servers:
  ```
  ./onapp2vhi list_onapp_vms
  ```

  * By specifying "_find=_" or "_props=_" parameter to get what you want:
    Examples:
      ```
      ./onapp2vhi list_onapp_vms --find="user_id=user_id"
      ./onapp2vhi list_onapp_vms --props={prop1},{prop2},{prop3}
      ```
  * this example will show you all VM's related to user with ID=7 and columns you specified in "--props":
    ```
    ./onapp2vhi list_onapp_vms --find="user_id=7" --props=identifier,hostname,memory,cpus,user_id,template_label,total_disk_size
    ```
  * this example will show you VM with specified identifier:
    ```
    ./onapp2vhi list_onapp_vms --find="identifier=lidqtfwggohyzk" --props=identifier,hostname,memory,cpus,user_id,template_label,total_disk_size
    ```

---

- ### Show all Users:
      ./onapp2vhi list_onapp_users
- the same logic is using for users:
- command will show you only user with id=7, login=admin or email=admin@example.com
  ```
    ./onapp2vhi list_onapp_users --find="id=7" 
  OR
    ./onapp2vhi list_onapp_users --find="login=admin"
  OR 
    ./onapp2vhi list_onapp_users --find="email=admin@example.com" 
  ```
- command will show you all VM's related to user with ID=7 and columns you specified in "vals":
  ```
  ./onapp2vhi list_onapp_users --find="login=admin" --props=id,email,login,roles,first_name,last_name
  ```

---

- ### HOW TO START MIGRATION:
  - Run migration script, the entry point:
      - This command will start whole migration process from OnApp CP to VHI (NOT recommended!):
        ```
          ./onapp2vhi migrate
        ```
      - If you want to migrate only one user and his VM's (Better choice is to migrate User by User):
        ```
        ./onapp2vhi migrate --user={user_id}
         example:
        ./onapp2vhi migrate --user=7
        ```
      - If you want to migrate only 1 user and only 1 VM:
        ```
        ./onapp2vhi migrate --user=7 --vm={vm_identifier}
        example:
        ./onapp2vhi migrate --user=7 --vm=sydarelogizozd
        ```
      - If you want to migrate only 1 user and only several VM's:
        ```
        ./onapp2vhi migrate --user=7 --vm=sydarelogizozd,lidqtfwggohyzk,dkktdwypbyupjs,rktgjliulxpwqt
        ```
      - After script finished, please take a look in logs file:
        ```
        ls -la ~/onapp2vhi/migration_logs/
        [output]:
        -rw-r--r--  1 user.user  staff   7671 Mar 30 14:19 full_log_30_03_2023_14_19_06.log
        -rw-r--r--  1 user.user  staff    197 Apr 12 17:04 migration_user_4.log
        -rw-r--r--  1 user.user  staff    245 Apr 12 17:04 migration_user_4_manual_migrate_vm.log
        ```
      - When you have case when you need to migrate all VM's into one project please use such command 
      (NOTE: before such migration, please create PROJECT manually in proper Domain):
      - 
        ```
        ./onapp2vhi migrate --user=7 --vm=sydarelogizozd,dkktdwypbyupjs --project={project_name}
        OR
        ./onapp2vhi migrate --user=7 --project=my_project
        ```
  - Full possible flags command:
      - `migrate` - stands for starting migration process
      - `--user=user_id` - stands for `User ID` at OnApp side
      - `--vm=vm_identifier_1,vm_identifier_2` - comma separated `list` of Virtual Machines to be migrated(can be
        empty, then all VM's will be migrated for specified user)
      - `--project=my_project` - stands for pre-created project `NAME` at VHI side
      - `--cloud_init_install` - Boolean flag, default value is `true`, set `false` to **NOT** install cloud_init
      - `--vz_guest_tools_install` - Boolean flag, default value is `true`, set `false` to **NOT** install vz-guest-tools
      - `--storage_policy` - stands for pre-created project `NAME` at VHI side
      - `--placement` - stands for pre-created project `NAME` at VHI side
        - **Examples**:
       
          Full possible flags:
          ```
          ./onapp2vhi migrate --user=7 --vm=sydarelogizozd,sy43relogizozd --storage_policy=not_default --project=my_project --vz_guest_tools_install=false --cloud_init_install=false
          ```        

          User + VM + network + disable cloud-init installation:
          ```
          ./onapp2vhi migrate --user=2 --vm=sydarelogizozd --cloud_init_install=false
          ```
          
          User + disable vz-guest-tools installation:
          ```
          ./onapp2vhi migrate --user=9 --vz_guest_tools_install=false
          ```

---

- ### Deactivate environment:
    - RUN in terminal `deactivate`

---

- ### Remove Logs on VHI side, sometimes there were issues with internal error:
    - Run command `rm -f ~/.vinfra/backend-api.svc.vstoragedomain/*`

---



