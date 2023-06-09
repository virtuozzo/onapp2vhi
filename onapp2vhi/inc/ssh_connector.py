import subprocess
import socket
import paramiko

from onapp2vhi.utilities.logs.logger import OnAppVHILogger
from time import sleep

NBYTES = 1024
CHANNEL_TIMEOUT = 3600  # How long we keep the channel opened
CONNECT_TIMEOUT = 300
logs = OnAppVHILogger()


def ssh_run(command: str, interactive=True, comment='', log_off=False, output=True):
    if comment:
        logs.info(comment)
    if not log_off:
        logs.info(f"Running: {command}", separator=True)
    if interactive:
        cmd_process = subprocess.Popen(command,
                                       shell=True,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)
        cmd_output = cmd_process.communicate()[0]
        exit_code = cmd_process.returncode
    else:
        cmd_output = ''
        exit_code = subprocess.call(command, shell=True)

    if cmd_output:
        _output = cmd_output.decode("utf-8", "ignore")
    else:
        _output = ''
    if exit_code == 0:
        if output:
            logs.info("Result [exit code: {}]: {}".format(str(exit_code), str(_output).strip('\n')))
    else:
        if output:
            logs.warn("Result [exit code: {}]: {}".format(str(exit_code), str(_output).strip('\n')))
    return [exit_code, _output]


_preferred_pubkeys = ("ssh-ed25519",
                      "ecdsa-sha2-nistp256",
                      "ecdsa-sha2-nistp384",
                      "ecdsa-sha2-nistp521",
                      "rsa-sha2-512",
                      "rsa-sha2-256",
                      "ssh-rsa",
                      "ssh-dss")
_preferred_pubkeys_old = ("ssh-ed25519",
                          "ecdsa-sha2-nistp256",
                          "ecdsa-sha2-nistp384",
                          "ecdsa-sha2-nistp521",
                          "ssh-rsa",
                          "rsa-sha2-512",
                          "rsa-sha2-256",
                          "ssh-dss")


class SSH:

    def __init__(self, **kwargs):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.host = kwargs.get("host")
        self.port = kwargs.get("port", 22)
        self.username = kwargs.get("username", "root")
        self.connect_timeout = kwargs.get("connect_timeout", CONNECT_TIMEOUT)
        self.channel_timeout = kwargs.get("channel_timeout", CHANNEL_TIMEOUT)
        self.pkey = paramiko.RSAKey.from_private_key_file(kwargs.get("ssh_key"))

    def _port_is_open(self, timeout=10):
        logs.debug(f"Check if port {self.port} is open on {self.host} host")
        connection = False
        for i in range(timeout):
            try:
                socket.setdefaulttimeout(timeout)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.host, int(self.port)))
                connection = True
                if connection:
                    break
            except socket.error as e:
                logs.error(e)
            finally:
                sock.close()
            sleep(10)
        return connection

    def _key_algorithms_handler(self):
        """
        Linux Based VM's
        Example of handler command:
        ssh root@10.119.0.14 -A -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' -t
        "echo -e \"HostKeyAlgorithms +ssh-rsa\nPubkeyAcceptedKeyTypes +ssh-rsa\" >> /etc/ssh/sshd_config;
            sudo systemctl restart ssh"
        :return:
        """
        from onapp2vhi.inc.helper import Helper
        logs.warn(msg='Trying to setup `PubkeyAcceptedAlgorithms` in the VM sshd_config. . .', )
        _cmd = (f"ssh root@{self.host} {Helper.SSH_OPTS.value} -t \"echo -e '\n#added by OnApp \nHostKeyAlgorithms"
                f" +ssh-rsa\\nPubkeyAcceptedKeyTypes +ssh-rsa\n' >> /etc/ssh/sshd_config; sudo systemctl restart ssh\"")
        [exit_status, output] = ssh_run(command=_cmd)
        logs.debug(msg='Waiting 5 seconds to restart sshd service. . .', separator=True)
        sleep(5)
        if not exit_status:
            try:
                self.client.connect(hostname=self.host,
                                    username=self.username,
                                    port=self.port,
                                    pkey=self.pkey,
                                    timeout=self.connect_timeout)
                return True

            except paramiko.AuthenticationException as AE:
                logs.error(f"{AE} - `PubkeyAcceptedAlgorithms Handler failed`, please take a look manually.")
                return False

        return False

    def _connect(self):
        paramiko.transport.Transport._preferred_pubkeys = _preferred_pubkeys
        paramiko.util.log_to_file("ssh_connection.log")
        if self._port_is_open():
            # Try to connect
            try:
                self.client.connect(hostname=self.host,
                                    username=self.username,
                                    port=self.port,
                                    pkey=self.pkey,
                                    timeout=self.connect_timeout)
                return True

            except paramiko.AuthenticationException as AE:
                logs.error(f"""{AE}\n The possible issues:
                    - password is required;
                    - your public key is absent on the server;
                    - host is empty;
                    - PubkeyAcceptedAlgorithms or PubkeyAcceptedKeyTypes are different on
                     remote server(try `sudo vi /etc/ssh/sshd_config` [HostKeyAlgorithms +ssh-rsa,
                      PubkeyAcceptedKeyTypes +ssh-rsa] and `sudo systemctl restart ssh`)
                    - your ssh-agent may missing your public key""")
                paramiko.transport.Transport._preferred_pubkeys = _preferred_pubkeys_old
                try:
                    logs.warn(msg='Trying OLD algorithm for SSH keys. . .')
                    self.client.connect(hostname=self.host,
                                        username=self.username,
                                        port=self.port,
                                        pkey=self.pkey,
                                        timeout=self.connect_timeout)
                    return True
                except paramiko.AuthenticationException:
                    return False

        return False

    def _receive_data(self, real_data=False):
        """
        Receive data from ssh channel
        :return:
        """
        # ToDo
        #  Develop Progress bar
        #  Cold migrate = "(0.00/100%)"./
        output = ""
        if self.channel.recv_ready():
            logs.debug("GET DATA...")
            data = self.channel.recv(NBYTES).decode("utf-8", "ignore")
            while data:
                if real_data:
                    logs.info(msg=data.strip())
                output += data
                try:
                    data = self.channel.recv(NBYTES).decode("utf-8", "ignore")
                except socket.timeout:
                    logs.error("Channel timeout exceeded...")
                    self.channel.close()
                    break
        if self.channel.recv_stderr_ready():
            logs.debug("GET ERROR...")
            data = self.channel.recv_stderr(NBYTES).decode("utf-8", "ignore")
            while data:
                if real_data:
                    logs.info(msg=data.strip())
                output += data
                try:
                    data = self.channel.recv_stderr(NBYTES).decode("utf-8", "ignore")
                except socket.timeout:
                    logs.error("Channel timeout exceeded...")
                    self.channel.close()
                    break

        return output

    def execute(self, command: str, real_data=False):
        """
        Execute any command via SSH on remote server
        :param command: "ls -la"
        :param real_data: bool True or False
        :return: int, str
        """
        self._connect()
        output = ""
        self.transport = self.client.get_transport()
        self.channel = self.transport.open_session()
        paramiko.agent.AgentRequestHandler(self.channel)
        self.channel.settimeout(self.channel_timeout)
        logs.debug(f"Channel timeout - {self.channel.timeout}")
        logs.debug(f"Default window size - {self.transport.default_window_size}")
        logs.info(f'HOST: {self.host} | PORT: {self.port}')
        logs.info(f'Running command: {command}')
        self.channel.exec_command(command)
        while True:
            data = self._receive_data(real_data=real_data)
            data = "\n".join([s for s in data.split("\n") if "Warning: Permanently added" not in s])
            output += data
            if self.channel.exit_status_ready():
                output += self._receive_data()
                exit_status = self.channel.recv_exit_status()
                break
            sleep(1)

        self.transport.close()
        self.client.close()
        if exit_status != 0:
            logs.warn(f'Exit code [{exit_status}] | Output: {output}')
        else:
            if len(output) >= 1000:
                logs.debug(f'Exit code [{exit_status}] | ... OUTPUT LENGTH IS TOO BIG ...')
            else:
                logs.debug(f'Exit code [{exit_status}] | Output: {output}')
        return exit_status, output
