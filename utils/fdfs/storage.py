from django.core.files.storage import Storage
from django.conf import settings
from fdfs_client.client import Fdfs_client


class FDFSStorage(Storage):
    """fdfs 文件储存类"""

    def __init__(self,client_conf=None, nginx_url=None):
        """初始化"""
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf
        if nginx_url is None:
            # print('空空空空空空空空空空空空空空空空空空空空')
            nginx_url = settings.FDFS_NGINX_URL
        self.nginx_url = nginx_url

    def _open(self,name,mode='rb'):
        """打开文件时使用"""
        pass

    def _save(self,name,content):
        """保存文件时使用"""

        client = Fdfs_client(self.client_conf)

        content = content.read()

        res = client.upload_by_buffer(content)

        if res['Status'] != 'Upload successed.':
            raise Exception('上传文件到fdfs失败')

        file_id = res['Remote file_id']

        return file_id

    def exists(self, name):
        return False

    def url(self, name):

        # print('空空空空空空空空空空空空空空空空空空空空')
        return self.nginx_url + name
