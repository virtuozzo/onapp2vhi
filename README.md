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
    - install tool dependecies into virtualenv
    ```
    (myenv) [onapp@cp onapp2vhi]$ pip install -r requirements.txt
    Collecting appdirs==1.4.3
      Using cached appdirs-1.4.3-py2.py3-none-any.whl (12 kB)
    Collecting bcrypt==4.0.0
      Using cached bcrypt-4.0.0-cp36-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (594 kB)
    .
    .
    .
    Installing collected packages: zipp, pycparser, importlib-metadata, cffi, urllib3, six, PyNaCl, pyflakes, pycodestyle, mccabe, importlib-resources, idna, filelock, distlib, cryptography, click, charset-normalizer, certifi, bcrypt, appdirs, virtualenv, typing, singledispatch, scandir, requests, pathlib2, paramiko, flake8, enum34, contextlib2, configparser, colorlog, click-default-group, chardet
    Successfully installed PyNaCl-1.5.0 appdirs-1.4.3 bcrypt-4.0.0 certifi-2021.10.8 cffi-1.15.1 chardet-4.0.0 charset-normalizer-2.0.12 click-7.1.2 click-default-group-1.2.2 colorlog-4.8.0 configparser-4.0.2 contextlib2-0.6.0.post1 cryptography-38.0.1 distlib-0.3.0 enum34-1.1.10 filelock-3.0.12 flake8-3.9.2 idna-2.10 importlib-metadata-1.6.0 importlib-resources-1.4.0 mccabe-0.6.1 paramiko-2.11.0 pathlib2-2.3.5 pycodestyle-2.7.0 pycparser-2.21 pyflakes-2.3.1 requests-2.27.1 scandir-1.10.0 singledispatch-3.4.0.3 six-1.14.0 typing-3.7.4.1 urllib3-1.26.11 virtualenv-20.0.18 zipp-1.2.0
    ```
    - install onapp2vhi CLI tool from source:
    ```
    (myenv) [onapp@cp onapp2vhi]$ pip install .
    Processing /home/onapp/yusri/src/onapp2vhi
      Preparing metadata (setup.py) ... done
    Building wheels for collected packages: onapp2vhi
      Building wheel for onapp2vhi (setup.py) ... done
      Created wheel for onapp2vhi: filename=onapp2vhi-0.1.dev0-py3-none-any.whl size=60255 sha256=3343ae7dbbd8816a3bf72e6db4549fc127a9066dfa1dbee9f097737d32b59092
      Stored in directory: /tmp/pip-ephem-wheel-cache-uyx8dv6h/wheels/98/c3/10/b31a96f0af812deb8b2057c40a50bd0a764566a19c5e96c8a8
    Successfully built onapp2vhi
    Installing collected packages: onapp2vhi
    Successfully installed onapp2vhi-0.1.dev0
    ```
  - at this point you will get an error due to missing config
  ```
  (myenv) [onapp@cp onapp2vhi]$ onapp2vhi --help
  [2023-03-31 10:24:04,794] ERROR    ##################################################
  [2023-03-31 10:24:04,794] ERROR    Config file does NOT exist: /home/onapp/myenv/lib/python3.6/site-packages/cfg/config.cfg
  Please create file with name "config.cfg" and provide properties as in "config-example.cfg" file
  [2023-03-31 10:24:04,794] ERROR    ##################################################

  ```
  - Please provide credentials related to OnApp and VHI clouds in the file __cfg/config.cfg__ (example: __cfg/config-example.cfg__)
    - `vi ./cfg/config.cfg`
    - save file
    - Temporary hack:
    ```
    ln -s ./cfg/config.cfg /home/onapp/myenv/lib/python3.6/site-packages/cfg/config.cfg
    ```
  - Copy files into project/scripts/ folder:
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
      - `openstack --insecure network set --disable-port-security {network-id}`
    - after migration finished revert changes:
      - `openstack --insecure network set --enable-port-security {network-id}`


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
  - ### Run migration script, this is the entry point:
    - Just type command:
        ```
        ./onapp2vhi migrate-all
      ```
    - If you want to migrate only one user and his VM's:
      ```
      ./onapp2vhi migrate-all --user=7
      ```
    - If you want to migrate only one user and only 1 VM:
      ```
      ./onapp2vhi migrate-all --user=7 --vm=sydarelogizozd
      ```
    - After script finished, please take a look in logs file:
      ```
      ~/onapp2vhi/migration_logs/
      ```
    - When you have case you need to migrate all VM's into one project please use such command:
      ```
      ./onapp2vhi migrate-all --user=7 --vm=sydarelogizozd --project=my_project
      ```
---
  - ### Deactivate environment:
    - RUN in terminal `deactivate`
---

   - ### Remove Logs on VHI side, sometimes there were issues with internal error:
     - Run command `rm -f ~/.vinfra/backend-api.svc.vstoragedomain/*`

---



