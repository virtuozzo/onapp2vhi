import os
from os.path import join, dirname, exists
from shutil import rmtree

from onapp2vhi.utilities.config import OnApp2VHIConfig
from onapp2vhi.inc.helper import Helper
from onapp2vhi.inc.ssh_connector import ssh_run
from onapp2vhi.inc.utils import exit_status_code_handler
from onapp2vhi.utilities.logs.logger import OnAppVHILogger


logs = OnAppVHILogger()


def update_vz_tools(cfg: OnApp2VHIConfig):
    package_path = dirname(__file__)

    iso_mount_point = '/tmp/vz-tools'
    iso_files = [
        'vz-guest-tools-lin',
        'vz-guest-tools-win',
    ]
    tar_destination_path = join(package_path, 'scripts')

    try:
        for file_name in iso_files:
            [exit_status, output] = ssh_run(
                command=f'scp -P{cfg.vhi_conf["cloud_ssh_port"]} '
                        f'{Helper.SCP_OPTS.value} '
                        f'root@{cfg.vhi_conf["cp_ip"]}:'
                        f'/usr/share/vz-guest-tools/{file_name}.iso /tmp/'
            )
            if not exit_status_code_handler(
                    exit_code=exit_status,
                    message=f'Copy {file_name}.iso failed. Output:\n\t{output}'
            ):
                return False

            if not exists(iso_mount_point):
                logs.info(f'Creating mount point: {iso_mount_point}')
                os.mkdir(iso_mount_point)

            [exit_status, output] = ssh_run(
                command=f'sudo mount /tmp/{file_name}.iso {iso_mount_point}'
            )
            if not exit_status_code_handler(
                    exit_code=exit_status,
                    message=f'Mounting {file_name}.iso failed. Output:\n\t{output}'
            ):
                return False

            [exit_status, output] = ssh_run(
                command=f'cd {iso_mount_point}; sudo tar -cf /tmp/{file_name}.tar ./*'
            )
            if not exit_status_code_handler(
                    exit_code=exit_status,
                    message=f'Creation {file_name}.tar failed. Output:\n\t{output}'
            ):
                return False

            [exit_status, output] = ssh_run(
                command=f'sudo umount {iso_mount_point}'
            )
            if not exit_status_code_handler(
                    exit_code=exit_status,
                    message=f'Unmounting {file_name}.iso failed. Output:\n\t{output}'
            ):
                return False

            [exit_status, output] = ssh_run(
                command=f'sudo chown {os.getuid()}.{os.getuid()} /tmp/{file_name}.tar'
            )
            if not exit_status_code_handler(
                    exit_code=exit_status,
                    message=f'Setting {file_name}.tar ownership failed. Output:\n\t{output}'
            ):
                return False

            if not exists(tar_destination_path):
                logs.info(f'Creating target path: {tar_destination_path}')
                os.mkdir(tar_destination_path)

            tar_file_path = join(package_path, 'scripts', f'{file_name}.tar')
            logs.info(f'Updating: {tar_file_path}')
            os.replace(f'/tmp/{file_name}.tar', tar_file_path)

        rmtree(f'{iso_mount_point}')
        for files in [ f'/tmp/{names}.iso' for names in iso_files]:
            os.unlink(files)
    except Exception as e:
        logs.error(e)
