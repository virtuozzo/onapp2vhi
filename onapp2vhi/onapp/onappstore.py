import re

from onapp2vhi.utilities.logs.logger import OnAppVHILogger


logs = OnAppVHILogger()


class OnAppStoreFailed(Exception):

    def __init__(self, command: str, exit_status: int, output: str):
        self.msg = f'onappstore command {command} failed {exit_status}, '\
                   f'output: {output}'


class InvalidUUID(Exception):
    pass


class OnAppStore:

    def __init__(self, ssh):
        super().__init__()

        self.onappstore_id = None
        self.locks = {}
        self.ssh = ssh

    def get_id(self):
        """
        Return onappstore id
        """
        if self.onappstore_id:
            return self.onappstore_id

        command = 'onappstore getid'
        output = self._execute_command(command)

        try:
            uuid = re.findall('\d+', re.findall('uuid=\d+', output)[0])[0]
        except IndexError:
            logs.error(f"The UUID was not found. Output:\n\t{output}")
            raise InvalidUUID()

        self.onappstore_id = uuid
        return self.onappstore_id

    def disk_info(self, disk_id: str):
        command = f'onappstore diskinfo uuid={disk_id}'

        output = self._execute_command(command)
        try:
            disk_status = re.search(r"\bstatus=(\d+)", output)
            status = int(disk_status.group(1))
        except IndexError:
            logs.error(f"The status was not found. Output:\n\t{output}")
            raise OnAppStoreFailed(command, 0, output)

        return status

    def acquire(self, disk_id: str, key: str):
        if not self.onappstore_id:
            self.get_id()

        command = f'onappstore acquire uuid={disk_id} key={key} '\
                  f'frontend_uuid={self.onappstore_id}'
        output = self._execute_command(command)
        self.locks.update({ disk_id: key })
        if 'SUCCESS' in output:
            return True
        else:
            return False

    def release(self, disk_id: str):
        if not self.onappstore_id:
            self.get_id()

        if disk_id in self.locks.keys():
            key = self.locks[disk_id]
            command = f'onappstore release uuid={disk_id} key={key} '\
                      f'frontend_uuid={self.onappstore_id}'
            output = self._execute_command(command)
            if 'SUCCESS' in output:
                del self.locks[disk_id]
                return True
            else:
                return False
        else:
            logs.warn(f'Disk {disk_id} already released')
            return True

    def online(self, disk_id: str, key: str = None):
        if not self.onappstore_id:
            self.get_id()

        command = f'onappstore online uuid={disk_id} '\
                  f'frontend_uuid={self.onappstore_id}'
        if key:
            command += f' key={key}'

        output = self._execute_command(command)
        return ('SUCCESS' in output)

    def offline(self, disk_id: str, key: str = None):
        command = f'onappstore offline uuid={disk_id}'
        if key:
            command += f' key={key}'

        output = self._execute_command(command)
        return ('SUCCESS' in output)

    def _execute_command(self, command):
        exit_status, output = self.ssh.execute(command=command)
        if exit_status:
            raise OnAppStoreFailed(command, exit_status, output)
        return output
