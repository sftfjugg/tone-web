import logging

import paramiko

from tone import settings

logger = logging.getLogger('sftp')


class SFTPClient(object):
    def __init__(self, host, user, password, port=22):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def upload_file(self, local_path, server_path, timeout=10):
        """
        上传文件，注意：不支持文件夹
        :param server_path: 远程路径，比如：/home/sdn/tmp.txt
        :param local_path: 本地路径，比如：D:/text.txt
        :param timeout: 超时时间(默认)，必须是int类型
        :return: bool
        """
        try:
            t = paramiko.Transport((self.host, self.port))
            t.connect(username=self.user, password=self.password)
            sftp = paramiko.SFTPClient.from_transport(t)
            sftp.banner_timeout = timeout
            self._mkdirs(server_path, sftp)
            sftp.put(local_path, server_path)
            t.close()
            return True
        except Exception as e:
            logger.error(f'sftp upload file[{local_path}] failed! error:{e}')
            return False

    def down_file(self, server_path, local_path, timeout=10):
        """
        下载文件，注意：不支持文件夹
        :param server_path: 远程路径，比如：/home/sdn/tmp.txt
        :param local_path: 本地路径，比如：D:/text.txt
        :param timeout: 超时时间(默认)，必须是int类型
        :return: bool
        """
        try:
            t = paramiko.Transport((self.host, 22))
            t.banner_timeout = timeout
            t.connect(username=self.user, password=self.password)
            sftp = paramiko.SFTPClient.from_transport(t)
            sftp.get(server_path, local_path, sftp)
            t.close()
            return True
        except Exception as e:
            logger.error(f'sftp download file[{local_path}] failed! error:{e}')
            return False

    @staticmethod
    def _mkdirs(server_path, sftp):
        path_list = server_path.split("/")[0:-1]
        for path_item in path_list:
            if not path_item:
                continue
            try:
                sftp.chdir(path_item)
            except Exception as e:
                logger.info(f'The directory does not exist, now create it.[{e}]')
                sftp.mkdir(path_item)
                sftp.chdir(path_item)


sftp_client = SFTPClient(
    settings.TONE_STORAGE_HOST,
    settings.TONE_STORAGE_USER,
    settings.TONE_STORAGE_PASSWORD,
    settings.TONE_STORAGE_SFTP_PORT
)
