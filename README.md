# onapp2vhi

------

### OnApp to VHI migration

---
* Setup local environment
  - Before running "./onapp2vhi" command please do next steps:
    - you should be in onapp2vhi project
    - RUN *sudo yum update*
    - RUN *sudo yum –y install python2-pip*
    - RUN *pip –V* (NOTE: you should see pip version ___pip 20.3.4 from /migrations/.venv/lib/python2.7/site-packages/pip (python 2.7)___)
    - RUN */usr/local/bin/python -m pip install --upgrade pip_*
    - RUN *pip install virtualenv*
    - RUN *virtualenv -p /usr/bin/python2.7 .venv* (NOTE: path may be different, please find where python 2.7 is located)
    - RUN *source .venv/bin/activate*
    - RUN *pip install --upgrade pip*
    - inside virtual env (you should see in console "(.venv) root@root #"):
      - RUN _pip install -r requirements.txt_
---
  - Please provide credentials related to OnApp and VHI clouds in the file __cfg/o2v_config.py__
    - vi ./cfg/o2v_config.py
    - save file
----
  * You have installed separate __python 2.7 virtual environment__ that will not affect global python requirements.
  * You have installed all needed packages and libraries into our virtual environment. 
  * You have provided credentials to access our clouds.
---
* Running migrations Examples:
  * ./onapp2vhi live-migrate --vm-identifier=qsykamkqqlpjbd
  * ./onapp2vhi cold-migrate --vm-identifier=qsykamkqqlpjbd
  * ./onapp2vhi install-bootloader --vm-identifier=qsykamkqqlpjbd
  * ./onapp2vhi install-bootloader-offline --vm-identifier=qsykamkqqlpjbd
  * ./onapp2vhi install-win-drivers --vm-identifier=qsykamkqqlpjbd
  * ./onapp2vhi install-win-drivers-offline --vm-identifier=qsykamkqqlpjbd
  * ./onapp2vhi template-migrate --label=Centos7
  * ./onapp2vhi list-onapp-vms
  * ./onapp2vhi list-onapp-users


