# migration-behave

## Setup virtualenv
```
pip3 install virtualenv
virtualenv -p python3 migration-venv
source migration-venv/bin/activate
pip3 install -r requirements.txt
```
## To run behave
Update config in `/behave/features/config.yaml` in order to run behave

Example: `behave features/ -t create_vm -f plain -f pretty`  
Help: `behave --help`
```
behave features/create_vm.feature
behave features/create_vm.feature:23 (per scenario)
behave (to run all features)
```