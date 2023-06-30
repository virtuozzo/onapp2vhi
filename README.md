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
    - install onapp2vhi CLI tool from source:
    ```
    (myenv) [onapp@cp onapp2vhi]$ pip install git+ssh://git@bitbucket.org/onappcore/onapp2vhi.git@v1.0.0
    Collecting git+ssh://****@bitbucket.org/onappcore/onapp2vhi.git@v1.0.0
      Cloning ssh://****@bitbucket.org/onappcore/onapp2vhi.git (to revision v1.0.0) to /tmp/pip-req-build-tcd_5faw
      Running command git clone -q 'ssh://****@bitbucket.org/onappcore/onapp2vhi.git' /tmp/pip-req-build-tcd_5faw
      Running command git checkout -b v1.0.0 --track origin/v1.0.0
      Switched to a new branch 'v1.0.0'
      Branch v1.0.0 set up to track remote branch v1.0.0 from origin.
      Resolved ssh://****@bitbucket.org/onappcore/onapp2vhi.git to commit c7ff0d423fa5b6446eb8e69fca5af295f81a8e00
      Installing build dependencies: started
      Installing build dependencies: finished with status 'done'
      Getting requirements to build wheel: started
      Getting requirements to build wheel: finished with status 'done'
      Preparing metadata (pyproject.toml): started
      Preparing metadata (pyproject.toml): finished with status 'done'
    Requirement already satisfied: requests==2.27.1 in ./venv/lib/python3.6/site-packages (from onapp2vhi==1.0.0) (2.27.1)
    Requirement already satisfied: colorlog==4.8.0 in ./venv/lib/python3.6/site-packages (from onapp2vhi==1.0.0) (4.8.0)
    Requirement already satisfied: importlib-resources==1.4.0 in ./venv/lib/python3.6/site-packages (from onapp2vhi==1.0.0) (1.4.0)
    Requirement already satisfied: paramiko==3.1.0 in ./venv/lib/python3.6/site-packages (from onapp2vhi==1.0.0) (3.1.0)
    Requirement already satisfied: click==7.1.2 in ./venv/lib/python3.6/site-packages (from onapp2vhi==1.0.0) (7.1.2)
    Requirement already satisfied: importlib-metadata in ./venv/lib/python3.6/site-packages (from importlib-resources==1.4.0->onapp2vhi==1.0.0) (4.8.3)
    Requirement already satisfied: zipp>=0.4 in ./venv/lib/python3.6/site-packages (from importlib-resources==1.4.0->onapp2vhi==1.0.0) (3.6.0)
    Requirement already satisfied: cryptography>=3.3 in ./venv/lib/python3.6/site-packages (from paramiko==3.1.0->onapp2vhi==1.0.0) (40.0.2)
    Requirement already satisfied: bcrypt>=3.2 in ./venv/lib/python3.6/site-packages (from paramiko==3.1.0->onapp2vhi==1.0.0) (4.0.1)
    Requirement already satisfied: pynacl>=1.5 in ./venv/lib/python3.6/site-packages (from paramiko==3.1.0->onapp2vhi==1.0.0) (1.5.0)
    Requirement already satisfied: idna<4,>=2.5 in ./venv/lib/python3.6/site-packages (from requests==2.27.1->onapp2vhi==1.0.0) (3.4)
    Requirement already satisfied: charset-normalizer~=2.0.0 in ./venv/lib/python3.6/site-packages (from requests==2.27.1->onapp2vhi==1.0.0) (2.0.12)
    Requirement already satisfied: urllib3<1.27,>=1.21.1 in ./venv/lib/python3.6/site-packages (from requests==2.27.1->onapp2vhi==1.0.0) (1.26.16)
    Requirement already satisfied: certifi>=2017.4.17 in ./venv/lib/python3.6/site-packages (from requests==2.27.1->onapp2vhi==1.0.0) (2023.5.7)
    Requirement already satisfied: cffi>=1.12 in ./venv/lib/python3.6/site-packages (from cryptography>=3.3->paramiko==3.1.0->onapp2vhi==1.0.0) (1.15.1)
    Requirement already satisfied: typing-extensions>=3.6.4 in ./venv/lib/python3.6/site-packages (from importlib-metadata->importlib-resources==1.4.0->onapp2vhi==1.0.0) (4.1.1)
    Requirement already satisfied: pycparser in ./venv/lib/python3.6/site-packages (from cffi>=1.12->cryptography>=3.3->paramiko==3.1.0->onapp2vhi==1.0.0) (2.21)
    Building wheels for collected packages: onapp2vhi
      Building wheel for onapp2vhi (pyproject.toml): started
      Building wheel for onapp2vhi (pyproject.toml): finished with status 'done'
      Created wheel for onapp2vhi: filename=onapp2vhi-1.0.0-py2.py3-none-any.whl size=4583729 sha256=1a7c49755c3b170aefe9ba960ecaad048c457827958bba3a4467ee707c9460da
      Stored in directory: /tmp/pip-ephem-wheel-cache-ul0oapdk/wheels/e6/91/36/97eaffd224cca1ef714dad490b42599841e1454d3d1b5bc5a6
    Successfully built onapp2vhi
    Installing collected packages: onapp2vhi
    Successfully installed onapp2vhi-1.0.0
    ```
  - create configuration file at `~/.config/onapp2vhi/config.ini` using the following template, provide credentials related to OnApp and VHI clouds
  ```
  [onapp]
  host = 69.168.239.170
  url = http://69.168.239.170
  api_key = here_is_yours_admin_api_key
  email = your_mail@gmail.com
  cp_ssh_port = 2222
  hv_ssh_port = 22

  [vhi]
  url = https://cvhi.onappdev.com:8888
  panel_url = https://cvhi.onappdev.com:8800
  api_path = /api/v2
  login = admin
  admin_ui_pwd = ui_admin_password
  hv_ip = 10.63.0.64
  cp_ip = 10.63.0.63
  network = public2
  cloud_ssh_port = 2222
  hv_ssh_port = 22
  linux_image = debian-10-openstack-amd64.qcow2
  windows_image = windows2012
  domain_id = 58fa18b2cefc4bad8a52f11008dfbf72
  vinfra_domain = Migration
  vinfra_project = migproj
  vhi_storage_policy = default
  vinfra_user = user_login
  vinfra_pass = user_pwd
  vinfra_domain_user = ''
  vinfra_domain_pass = ''

  #Network ID for migration VM's, you can get it on VHI cloud
  migration_network_id = 5afcb27b-1c92-4561-a81c-fcf4f89bd543

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
  * **Providers**:
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
      - `--project=my_project` - stands for pre-created project `NAME` at VHI side
      - `--cloud_init_install` - Boolean flag, default value is `true`, set `false` to **NOT** install cloud_init
      - `--vz_guest_tools_install` - Boolean flag, default value is `true`, set `false` to **NOT** install vz-guest-tools
      - `--storage_policy` - stands for pre-created project `NAME` at VHI side
      - `--placement` - stands for pre-created project `NAME` at VHI side
        - **Examples**:

          Full possible flags:
          ```
          onapp2vhi migrate --user=7 --vm=sydarelogizozd,sy43relogizozd --storage_policy=not_default --project=my_project --vz_guest_tools_install=false --cloud_init_install=false
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

- ### Deactivate environment:
    - RUN in terminal `deactivate`

---

- ### Remove Logs on VHI side, sometimes there were issues with internal error:
    - Run command `rm -f ~/.vinfra/backend-api.svc.vstoragedomain/*`

---



