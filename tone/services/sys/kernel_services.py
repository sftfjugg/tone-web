# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import re
from urllib import request, error

from django.db.models import Q

from tone.core.common.constant import YUM_PACKAGE_REPOSITORY_URL, KERNEL_URL
from tone.models import KernelInfo
from tone.core.common.services import CommonService
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import KernelException


class KernelInfoService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        q &= Q(id=data.get('kernel_id')) if data.get('kernel_id') else q
        q &= Q(version__icontains=data.get('version')) if data.get('version') else q
        q &= Q(release=data.get('release')) if data.get('release') else q
        q &= Q(enable=data.get('enable')) if data.get('enable') else q
        q &= Q(update_user=data.get('update_user')) if data.get('update_user') else q
        q &= Q(description=data.get('description')) if data.get('description') else q
        q &= Q(creator=data.get('creator')) if data.get('creator') else q
        return queryset.filter(q)

    def update(self, data, operator):
        kernel_id = data.get('kernel_id')
        assert kernel_id, KernelException(ErrorCode.KERNEL_ID_LACK)
        self.check_id(kernel_id)
        obj = KernelInfo.objects.get(id=kernel_id)
        for key, value in data.items():
            if key == 'version':
                if value != obj.version:
                    self.check_name(value)
            if hasattr(obj, key):
                setattr(obj, key, value)
        obj.update_user = operator.id
        obj.save()

    def create(self, data, operator):
        version = data.get('version')
        kernel_link = data.get('kernel_link')
        devel_link = data.get('devel_link')
        headers_link = data.get('headers_link')
        release = data.get('release', True)
        enable = data.get('enable', True)
        creator = operator.id
        description = data.get('description', None)
        assert version, KernelException(ErrorCode.KERNEL_VERSION_LACK)
        self.check_name(version)
        KernelInfo.objects.create(
            version=version,
            kernel_link=kernel_link,
            devel_link=devel_link,
            headers_link=headers_link,
            release=release,
            enable=enable,
            creator=creator,
            description=description,
        )

    def delete(self, data, operator):
        kernel_id = data.get('kernel_id')
        assert kernel_id, KernelException(ErrorCode.KERNEL_ID_LACK)
        self.check_id(kernel_id)
        KernelInfo.objects.get(id=kernel_id).delete()

    @staticmethod
    def check_id(kernel_id):
        obj = KernelInfo.objects.filter(id=kernel_id)
        if not obj.exists():
            raise KernelException(ErrorCode.KERNEL_NONEXISTENT)

    @staticmethod
    def check_name(version):
        obj = KernelInfo.objects.filter(version=version)
        if obj.exists():
            raise KernelException(ErrorCode.KERNEL_VERSION_DUPLICATION)

    def sync_kernel(self, data, operator):
        kernel_version_list = data.get('version_list')
        success, kernel_info = self.get_kernel_info()
        creator = operator.id
        if success:
            tmp_link = ''
            for kernel_version in kernel_version_list:
                for tmp_kernel in kernel_info:
                    # 拼接版本下载路径
                    if not tmp_kernel.startswith('kernel'):
                        tmp_link = '{}{}kernel/'.format(YUM_PACKAGE_REPOSITORY_URL, tmp_kernel)
                        continue
                    # 找到要同步的内核版本, 进行同步
                    if kernel_version == tmp_kernel.split('.rpm')[0].split('kernel-')[-1]:
                        # 拼接路径和内核版本
                        kernel_link = '{}{}'.format(tmp_link, tmp_kernel)
                        devel_link = kernel_link.replace('kernel', 'kernel-devel')
                        headers_link = kernel_link.replace('kernel', 'kernel-headers')
                        # 内核版本中不存在, 创建 / 存在， 更新
                        if not KernelInfo.objects.filter(version=kernel_version).exists():
                            kernel_info = KernelInfo.objects.create(version=kernel_version,
                                                                    kernel_link=kernel_link,
                                                                    devel_link=devel_link,
                                                                    headers_link=headers_link,
                                                                    creator=creator,
                                                                    enable=True,
                                                                    release=False)
                        else:
                            is_enable = KernelInfo.objects.filter(version=kernel_version, enable=True).exists()
                            is_release = KernelInfo.objects.filter(version=kernel_version, release=True).exists()
                            KernelInfo.objects.filter(version=kernel_version).update(kernel_link=kernel_link,
                                                                                     devel_link=devel_link,
                                                                                     headers_link=headers_link,
                                                                                     update_user=creator,
                                                                                     enable=is_enable,
                                                                                     release=is_release)
                        break
                else:
                    return False, '同步失败, 内核 {} 未找到'.format(str(kernel_version))
        else:
            return False, '同步失败：{}'.format(str(kernel_info))
        return True, '同步成功'

    @staticmethod
    def get_kernel_info():
        """获取内核信息"""
        kernel_info_list = list()
        sub_link_list = ['current/', 'stable/', 'test/']
        pattern = re.compile(r'<li><a href="(.*)">.*</a></li>')
        try:
            for sub_link in sub_link_list:
                link = '{}{}kernel/'.format(KERNEL_URL, sub_link)
                req = request.urlopen(link)
                result = req.read()
                kernel_info_list.extend(re.findall(pattern, result.decode()))
        except error.HTTPError as error_info:
            return False, error_info
        except error.URLError as error_info:
            return False, error_info
        except Exception as error_info:
            return False, error_info
        return True, kernel_info_list
