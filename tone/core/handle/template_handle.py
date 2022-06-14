# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import random
import string

from tone.models import JobType, Project
from tone.models import TestTemplate
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import JobTestException
from tone.core.handle.base_handle import BaseHandle
from tone.core.handle.job_handle import JobDataHandle


class TestTemplateHandle(BaseHandle):

    def pack_custom(self):  # noqa: C901
        """
        组装data_dic、tag_list数据
        """
        self.data_dic['job_type_id'] = job_type_id = self.data.get('job_type', None)
        assert job_type_id, ValueError(ErrorCode.TYPE_ID_LACK)
        job_type = JobType.objects.get(id=job_type_id)
        self.ws_id = job_type.ws_id
        self.data_dic['ws_id'] = self.ws_id
        if 'name' in self.data:
            self.data_dic['job_name'] = self.data.get('name')
        if 'baseline' in self.data or 'baseline_id' in self.data:
            self.data_dic['baseline_id'] = self.data.get('baseline') or self.data.get('baseline_id')
        if 'baseline_job_id' in self.data:
            self.data_dic['baseline_job_id'] = self.data.get('baseline_job_id')
        if 'cleanup_info' in self.data:
            self.data_dic['cleanup_info'] = self.data.get('cleanup_info')
        if 'tags' in self.data and isinstance(self.data.get('tags'), list):
            [self.tag_list.append(tag) for tag in self.data.get('tags')]
        if 'template_name' in self.data:
            name_obj = TestTemplate.objects.filter(name=self.data.get('template_name'), ws_id=self.ws_id)
            if self.obj:
                if name_obj.exists() and self.obj.name != self.data.get('template_name'):
                    raise JobTestException(ErrorCode.TEMPLATE_NAME_EXIST)
            else:
                if name_obj.exists():
                    raise JobTestException(ErrorCode.TEMPLATE_NAME_EXIST)
            self.data_dic['name'] = self.data.get('template_name')
        else:
            self.data_dic['name'] = random.sample(string.ascii_letters + string.digits, 18)
        self.data_dic['description'] = self.data.get('description', '')
        self.data_dic['enable'] = self.data.get('enable', True)
        if 'iclone_info' in self.data:
            iclone_info = self.data.get('iclone_info')
            creator_name = self.operator.first_name if self.operator.first_name else self.operator.last_name
            iclone_info['create_from'] = creator_name
            self.data_dic['iclone_info'] = self.data.get('iclone_info')
        else:
            self.data_dic['iclone_info'] = dict()
        self.data_dic['kernel_info'] = self.data.get('kernel_info', dict())
        self.data_dic['build_pkg_info'] = self.data.get('build_pkg_info', dict())
        self.data_dic['script_info'] = self.data.get('script_info', list())
        self.data_dic['rpm_info'] = self.data.get('rpm_info', list())
        self.data_dic['report_name'], self.data_dic['report_template_id'] = self.get_report_info()
        if self.data.get('schedule_info'):
            self.data_dic['schedule_info'] = self.data.get('schedule_info', None)
        self.data_dic['monitor_info'] = JobDataHandle.restructure_monitor_info(self.data.get('monitor_info', list()))
        self.data_dic['need_reboot'] = self.data.get('need_reboot', False)
        self.data_dic['console'] = self.data.get('console', False)
        self.data_dic['notice_info'] = self.pack_notice_info(email=self.data.get('email_notice', None
                                                                                 ) or self.data.get('email', None),
                                                             ding=self.data.get('ding_msg', None) or self.data.get(
                                                                 'ding_token', None),
                                                             subject=self.data.get(
                                                                 'notice_name', None) or self.data.get(
                                                                 'notice_subject', None))
        self.data_dic['kernel_version'] = self.data.get('kernel_version')
        self.data_dic['env_info'] = self.pack_env_info(self.data.get('env_info')) if self.data.get(
            'env_info') else dict()
        self.data_dic['server_provider'] = self.provider = job_type.server_type
        if self.data.get('project'):
            project_id = self.data.get('project')
        else:
            project_id = Project.objects.filter(is_default=True, ws_id=self.ws_id).first().id \
                if Project.objects.filter(is_default=True, ws_id=self.ws_id).exists() else None
        self.data_dic['project_id'] = project_id
        self.data_dic['product_id'] = self.get_product(self.data_dic['project_id'])
        self.data_dic['callback_api'] = self.data.get('callback_api', None)

    def pack_custom_suite_case(self):
        """
        组装JobTest Suite Case关联数据
        """
        provider = self.provider
        test_config = self.data.get('test_config', list())
        if not isinstance(test_config, list):
            JobTestException(ErrorCode.TEST_CONF_LIST)
        for suite in test_config:
            self.pack_suite(suite, provider)
