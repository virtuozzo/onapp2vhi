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

- Before running "onapp2vhi" command please do next steps:
    - ensure you have access to virtualenv (installed from os distro)
    ```
    [onapp@cp ~]$ which virtualenv
    /bin/virtualenv
    [onapp@cp ~]$ virtualenv --version
    15.1.0
    [onapp@cp ~]$ yum list | grep virtualenv
    python-virtualenv.noarch                15.1.0-7.el7_9                @updates
    ```
    - create your virtual env (replace `myenv` in example below with path to your desired environment):
    ```
    [onapp@cp onapp2vhi]$ mkdir -p ../myenv/
    [onapp@cp onapp2vhi]$ virtualenv -p python3 ../myenv/
    Running virtualenv with interpreter /bin/python3
    Using base prefix '/usr'
    New python executable in /home/onapp/myenv/bin/python3
    Also creating executable in /home/onapp/myenv/bin/python
    Installing setuptools, pip, wheel...done.
    ```
    - activate virtualenv and update pip:
    ```
    [onapp@cp onapp2vhi]$ source ../myenv/bin/activate
    (myenv) [onapp@cp onapp2vhi]$ pip install --upgrade pip
    Cache entry deserialization failed, entry ignored
    Collecting pip
      Using cached https://files.pythonhosted.org/packages/a4/6d/6463d49a933f547439d6b5b98b46af8742cc03ae83543e4d7688c2420f8b/pip-21.3.1-py3-none-any.whl
    Installing collected packages: pip
      Found existing installation: pip 9.0.1
        Uninstalling pip-9.0.1:
          Successfully uninstalled pip-9.0.1
    Successfully installed pip-21.3.1
    You are using pip version 21.3.1, however version 23.0.1 is available.
    You should consider upgrading via the 'pip install --upgrade pip' command.
    ```
    - install onapp2vhi CLI tool from source (GitHub):
    ```
    # Virtuozzo Infrastructure (o2v-ps) — this branch
    (myenv) [onapp@cp onapp2vhi]$ pip install git+https://github.com/virtuozzo/onapp2vhi.git@o2v-ps

    # Latest release line (master)
    (myenv) [onapp@cp onapp2vhi]$ pip install git+https://github.com/virtuozzo/onapp2vhi.git@master
    ```
  - create configuration file at `~/.config/onapp2vhi/config.ini` using the following template, provide credentials related to OnApp and VHI clouds
  ```
  [onapp]
  host = 127.0.0.1
  url = http://127.0.0.1
  api_key = here_is_yours_admin_api_key
  email = your_mail@gmail.com
  cp_ssh_port = 2222
  hv_ssh_port = 22

  [vhi]
  url = https://cvhi.onapp.virtuozzo.com:8888
  panel_url = https://cvhi.onapp.virtuozzo.com:8800
  api_path = /api/v2
  login = admin
  admin_ui_pwd = ui_admin_password
  hv_ip = 10.0.0.2
  cp_ip = 127.0.0.1
  cp_ip_internal = 192.168.0.1
  network = public2
  cloud_ssh_port = 2222
  hv_ssh_port = 22
  linux_image = debian-10-openstack-amd64.qcow2
  windows_image = windows2012
  domain_id = 00000000000000000000000000000000
  vinfra_domain = Migration
  vinfra_project = migproj
  vhi_storage_policy = default
  vinfra_user = user_login
  vinfra_pass = user_pwd
  vinfra_domain_user = ''
  vinfra_domain_pass = ''
  remove_disk_on_termination = yes


  #Network ID for migration VM's, you can get it on VHI cloud
  migration_network_id = 00000000-0000-0000-0000-000000000001

  #Security Group ID specified to use for 2nd, 3rd, ... NIC's
  vhi_secondary_security_group = 00000000-0000-0000-0000-000000000002

  [key]
  ssh_key = path/to/your/ssh_key/id_rsa
  ```
- run next commands under `onapp` user:
    - `su - onapp`
    - `export SSH_AUTH_SOCK=/onapp/interface/tmp/onapp-ssh-agent.socket`
    - `echo "export SSH_AUTH_SOCK=/onapp/interface/tmp/onapp-ssh-agent.socket" >> /home/onapp/.bashrc `

* You have installed separate __python 3 virtual environment__ that will not affect global python requirements.
* You have installed all needed packages and libraries into our virtual environment.
* You have provided credentials to access our clouds.

## Setup User on VHI Side

- run virtual env [~/onapp2vhi]# source .venv/bin/activate
    - run next command: `(.venv)[~/onapp2vhi]# onapp2vhi create_service_user`
    - user for migrations will be created and saved into `~/.config/onapp2vhi/config.ini` file with credentials
- On VHI server do next steps:
    - set into .bashrc file:
        - `source /etc/kolla/admin-openrc.sh`
    - take an ID all your networks and do next:
        - `openstack --insecure network set --disable-port-security network_id`
    - after migration finished revert changes:
        - `openstack --insecure network set --enable-port-security network_id`

---
---

## Running onapp2vhi examples:
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
  onapp2vhi --help
  OR
  onapp2vhi --h
  OR
  onapp2vhi help
  OR
  onapp2vhi man
  ```

- Currently, migration tool provides next commands:
  * **Commands**:
    * `create_service_user` - command will create special user under the hood for migration and save his credentials into config file
    * `list-onapp-users` - get and show all user at OnApp cloud
    * `list-onapp-vms` - get and show all virtual machines at OnApp cloud
    * `migrate` - entry point to start migration

---

- ### Show all Virtual Servers:
  ```
  onapp2vhi list-onapp-vms
  ```

  * By specifying "_find=_" or "_props=_" parameter to get what you want:
    Examples:
      ```
      onapp2vhi list-onapp-vms --find="user_id=user_id"
      onapp2vhi list-onapp-vms --props={prop1},{prop2},{prop3}
      ```
  * this example will show you all VM's related to user with ID=7 and columns you specified in "--props":
    ```
    onapp2vhi list-onapp-vms --find="user_id=7" --props=identifier,hostname,memory,cpus,user_id,template_label,total_disk_size
    ```
  * this example will show you VM with specified identifier:
    ```
    onapp2vhi list-onapp-vms --find="identifier=lidqtfwggohyzk" --props=identifier,hostname,memory,cpus,user_id,template_label,total_disk_size
    ```

---

- ### Show all Users:
      onapp2vhi list-onapp-users
- the same logic is using for users:
- command will show you only user with id=7, login=admin or email=admin@example.com
  ```
    onapp2vhi list-onapp-users --find="id=7"
  OR
    onapp2vhi list-onapp-users --find="login=admin"
  OR
    onapp2vhi list-onapp-users --find="email=admin@example.com"
  ```
- command will show you all VM's related to user with ID=7 and columns you specified in "vals":
  ```
  onapp2vhi list-onapp-users --find="login=admin" --props=id,email,login,roles,first_name,last_name
  ```

---

- ### HOW TO START MIGRATION:
  - Run migration script, the entry point:
      - This command will start whole migration process from OnApp CP to VHI (NOT recommended!):
        ```
          onapp2vhi migrate
        ```
      - If you want to migrate only one user and his VM's (Better choice is to migrate User by User):
        ```
        onapp2vhi migrate --user={user_id}
         example:
        onapp2vhi migrate --user=7
        ```
      - If you want to migrate only 1 user and only 1 VM:
        ```
        onapp2vhi migrate --user=7 --vm={vm_identifier}
        example:
        onapp2vhi migrate --user=7 --vm=sydarelogizozd
        ```
      - If you want to migrate only 1 user and only several VM's:
        ```
        onapp2vhi migrate --user=7 --vm=sydarelogizozd,lidqtfwggohyzk,dkktdwypbyupjs,rktgjliulxpwqt
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
        onapp2vhi migrate --user=7 --vm=sydarelogizozd,dkktdwypbyupjs --project={project_name}
        OR
        onapp2vhi migrate --user=7 --project=my_project
        ```
  - Full possible flags command:
      - `migrate` - stands for starting migration process
      - `--user=user_id` - stands for `User ID` at OnApp side
      - `--vm=vm_identifier_1,vm_identifier_2` - comma separated `list` of Virtual Machines to be migrated(can be
        empty, then all VM's will be migrated for specified user)
      - `--vm-ssh-port` - optional custom virtual server ssh port number (default: 22)
      - `--project=my_project` - stands for pre-created project `NAME` at VHI side
      - `--network=<network name / ID> - stands for appliance network name or ID in VHI
      - `--cloud_init_install` - Boolean flag, default value is `true`, set `false` to **NOT** install cloud_init
      - `--vz_guest_tools_install` - Boolean flag, default value is `true`, set `false` to **NOT** install vz-guest-tools
      - `--storage_policy` - Defaults to string `default` when not provided. When it is specified, it refers to storage policy defined in VHI to be used in the VM creation.
      - `--placement` - Defaults to string `default` when not provided. When it is specified, it refers to placement defined in VHI to be used in the VM creation.
      - `--flavor` - Flavor defined in VHI for VM creation. Defaults to string `default` when not provided, where it will use current OnApp VM specification for a flavor.
      - `--hotplug` - Enable VM CPU and RAM hot plug for the create VHI VM
      - `--strict-ip-pool-match` - strictly matches appliance network ip pool range between OnApp and VHI
      - `--no-network-create` - prevents tool from creating a new virtual network for migrating virtual servers
        - **Examples**:

          Full possible flags:
          ```
          onapp2vhi migrate --user=7 --vm=sydarelogizozd,sy43relogizozd --vm-ssh-port 2722 --storage_policy=not_default --project=my_project --vz_guest_tools_install=false --cloud_init_install=false --placement=some_placement --flavor=4cpu_32gb --hotplug
          ```

          User + VM + disable cloud-init installation:
          ```
          onapp2vhi migrate --user=2 --vm=sydarelogizozd --cloud_init_install=false
          ```

          User + disable vz-guest-tools installation:
          ```
          onapp2vhi migrate --user=9 --vz_guest_tools_install=false
          ```

---

- ### Modifying configs in `~/.config/onapp2vhi/config.ini`:
    - RUN in terminal `onapp2vhi-config`

---

- ### Deactivate environment:
    - RUN in terminal `deactivate`

---

- ### Remove Logs on VHI side, sometimes there were issues with internal error:
    - Run command `rm -f ~/.vinfra/backend-api.svc.vstoragedomain/*`

---

- ### Known issues:
    - Debian 9 (Stretch) VS requires `grub2` package to be installed before VS can be migrated successfully (not installed by default). i.e.:
    ```
    # apt-cache policy grub2
    grub2:
      Installed: (none)
      Candidate: 2.02~beta3-5+deb9u2
      Version table:
         2.02~beta3-5+deb9u2 500
            500 http://archive.debian.org/debian stretch/main amd64 Packages
    # grub-install --version
    grub-install (GNU GRUB 0.97)
    ```
    - At the time of this writing live Debian 9 repositories are no longer available so `/etc/apt/sources.list` should be adjusted to the following:
    ```
    deb http://archive.debian.org/debian/ stretch main contrib non-free
    deb http://archive.debian.org/debian/ stretch-proposed-updates main contrib non-free
    deb http://archive.debian.org/debian-security stretch/updates main contrib non-free
    ```
    - Install `grub2` package. Follow the prompted instruction and reboot VS on completion before VS is migrated. i.e.:
    ```
    # apt update; apt install grub2
    # reboot
    ```
