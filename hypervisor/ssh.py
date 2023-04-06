import os
import paramiko
from six import BytesIO
from hypervisor import logger


class SSHConnect:
    """Extended SSHClient allowing custom methods"""

    def __init__(self, host, user, pwd=None, rsafile=None, port=22, timeout=1800):
        """
        :param str host: The hostname or ip of the server to establish connection.
        :param str user: The username to use when connecting.
        :param str pwd: The password to use when connecting.
        :param str rsafile: The path of the ssh private key to use when connecting to the server
        :param int port: The server port to connect to, the default port is 22.
        :param int timeout: Time to wait for the ssh command to finish.
        """
        self.host = host
        self.user = user
        self.pwd = pwd
        self.rsa = rsafile
        self.port = port
        self.timeout = timeout
        self.err = "passwd or rsafile can not be None"

    def _connect(self):
        """SSH command execution connection"""
        if self.pwd:
            return self.pwd_connect()
        elif self.rsa:
            return self.rsa_connect()
        else:
            raise ConnectionError(self.err)

    def _transfer(self):
        """Sftp download/upload execution connection"""
        if self.pwd:
            return self.pwd_transfer()
        elif self.rsa:
            return self.rsa_transfer()
        else:
            raise ConnectionError(self.err)

    def pwd_connect(self):
        """SSH command execution connection by password"""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.host, self.port, self.user, self.pwd, timeout=self.timeout)
        return ssh

    def rsa_connect(self):
        """SSH command execution connection by key file"""
        pkey = paramiko.RSAKey.from_private_key_file(self.rsa)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.host, self.port, self.user, pkey=pkey, timeout=self.timeout)
        return ssh

    def pwd_transfer(self):
        """Sftp download/upload execution connection by password"""
        transport = paramiko.Transport(self.host, self.port)
        transport.connect(username=self.user, password=self.pwd)
        sftp = paramiko.SFTPClient.from_transport(transport)
        return sftp, transport

    def rsa_transfer(self):
        """Sftp download/upload execution connection by key file"""
        pkey = paramiko.RSAKey.from_private_key_file(self.rsa)
        transport = paramiko.Transport(self.host, self.port)
        transport.connect(username=self.user, pkey=pkey)
        sftp = paramiko.SFTPClient.from_transport(transport)
        return sftp, transport

    def runcmd(self, cmd):
        """Executes SSH command on remote hostname.
        :param str cmd: The command to run
        """
        ssh = self._connect()
        logger.info(">>> {}".format(cmd))
        stdin, stdout, stderr = ssh.exec_command(cmd)
        code = stdout.channel.recv_exit_status()
        stdout, stderr = stdout.read(), stderr.read()
        ssh.close()
        if not stderr:
            logger.info("<<< stdout\n{}".format(stdout.decode()))
            return code, stdout.decode()
        else:
            logger.info("<<< stderr\n{}".format(stderr.decode()))
            return code, stderr.decode()

    def get_file(self, remote_file, local_file):
        """Download a remote file to the local machine."""
        sftp, conn = self._transfer()
        sftp.get(remote_file, local_file)
        conn.close()

    def put_file(self, local_file, remote_file):
        """Upload a local file to a remote machine
        :param local_file: either a file path or a file-like object to be uploaded.
        :param remote_file: a remote file path where the uploaded file will be placed.
        """
        sftp, conn = self._transfer()
        sftp.put(local_file, remote_file)
        conn.close()

    def put_dir(self, local_dir, remote_dir):
        """Upload all files from directory to a remote directory
        :param local_dir: all files from local path to be uploaded.
        :param remote_dir: a remote path where the uploaded files will be placed.
        """
        sftp, conn = self._transfer()
        for root, dirs, files in os.walk(local_dir):
            for filespath in files:
                local_file = os.path.join(root, filespath)
                a = local_file.replace(local_dir, "")
                remote_file = os.path.join(remote_dir, a)
                try:
                    sftp.put(local_file, remote_file)
                except Exception as e:
                    sftp.mkdir(os.path.split(remote_file)[0])
                    sftp.put(local_file, remote_file)
            for name in dirs:
                local_path = os.path.join(root, name)
                a = local_path.replace(local_dir, "")
                remote_path = os.path.join(remote_dir, a)
                try:
                    sftp.mkdir(remote_path)
                except Exception as e:
                    logger.info(e)
        conn.close()
