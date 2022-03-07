from tone.core.common.schemas import BaseSchema


class BaselineSchema(BaseSchema):

    def get_param_data(self):
        return {
            'test_type': {'type': str, 'required': True, 'example': 'functional',
                          'desc': '测试类型（functional/performance）'},
            'server_provider': {'type': str, 'required': True,
                                'example': 'aligroup', 'desc': '机器类型（aligroup/aliyun）'},
            'ws_id': {'type': str, 'required': True, 'example': 'OS-kernel-test', 'desc': '关联Workspace'},
            'id': {'type': int, 'required': False, 'example': '1', 'desc': '根据基线id搜索'},
            'name': {'type': str, 'required': False, 'example': 'x86_64',
                     'desc': '根据基线名称搜索'},
            'version': {'type': str, 'required': False, 'example': '3.10.', 'desc': '根据产品版本搜索'},
        }

    def get_body_data(self):
        return {
            'ws_id': {'type': str, 'required': True, 'example': 'OS-kernel-test', 'desc': '关联Workspace'},
            'name': {'type': str, 'required': True, 'example': 'x86_64',
                     'desc': '基线名称'},
            'version': {'type': str, 'required': True, 'example': '3.10.', 'desc': '产品版本'},
            'description': {'type': str, 'required': False, 'example': '功能要求场景', 'desc': '基线描述'},
            'test_type': {'type': str, 'required': True, 'example': 'functional',
                          'desc': '测试类型（functional/performance）'},
            'server_provider': {'type': str, 'required': True,
                                'example': 'aligroup', 'desc': '机器类型（aligroup/aliyun）'}
        }

    def get_update_data(self):
        return {
            'baseline_id': {'type': int, 'required': True, 'example': '1', 'desc': '基线的id'},
            'name': {'type': str, 'required': True,
                     'example': 'x86_64', 'desc': '基线名称'},
            'description': {'type': str, 'required': False, 'example': '功能要求场景', 'desc': '基线描述'}
        }

    def get_delete_data(self):
        return {
            'baseline_id': {'type': int, 'required': True, 'example': '1', 'desc': '要删除基线的id'}
        }


class FuncBaselineDetailSchema(BaseSchema):

    def get_param_data(self):
        return {
            "baseline_id": {'type': int, 'required': True, 'example': 1, 'desc': '要展开suite的基线id'},
            "test_suite_id": {'type': int, 'required': False, 'example': 54, 'desc': '要展开conf的test_suite_id'},
            "test_case_id": {'type': int, 'required': False, 'example': 307, 'desc': '要展开failcase的test_case_id'},
        }

    def get_body_data(self):
        return {
            'baseline_name_list': {'type': list, 'required': True,
                                   'example': ['testbaseline-functional', '3.10.0-327.ali201'],
                                   'desc': '要加入基线分类名称列表'},
            'test_type': {'type': str, 'required': True, 'example': 'functional',
                          'desc': '测试类型（functional/performance）'},
            'server_provider': {'type': str, 'required': True,
                                'example': 'aligroup', 'desc': '机器类型（aligroup/aliyun）'},
            'ws_id': {'type': str, 'required': True, 'example': 'OS-kernel-test', 'desc': '关联Workspace'},
            'test_job_id': {'type': int, 'required': True, 'example': '8', 'desc': '关联JOB ID'},
            'test_suite_id': {'type': int, 'required': True, 'example': '54', 'desc': '关联SUITE ID'},
            'test_case_id': {'type': int, 'required': True, 'example': '307', 'desc': '关联CASE ID'},
            "result_id": {'type': int, 'required': True, 'example': '1', 'desc': '功能结果详情的id'},
            'impact_result': {'type': bool, 'required': True, 'example': 'True', 'desc': '是否影响基线'},
            'bug': {'type': str, 'required': False, 'example': 'xxx', 'desc': 'Aone记录'},
            'description': {'type': str, 'required': False, 'example': '什么缺陷', 'desc': '缺陷描述'},
            'note': {'type': str, 'required': False, 'example': '备注', 'desc': '备注'}
        }

    def get_update_data(self):
        return {
            'id': {'type': int, 'required': True, 'example': '1', 'desc': '要删除功能详情的id'},
            'impact_result': {'type': bool, 'required': True, 'example': 'True', 'desc': '是否影响基线'},
            'bug': {'type': str, 'required': False, 'example': 'xxx', 'desc': 'Aone记录'},
            'description': {'type': str, 'required': False, 'example': '描述', 'desc': '问题描述'}
        }

    def get_delete_data(self):
        return {
            'id': {'type': int, 'required': True, 'example': '1', 'desc': '要删除功能详情的id'}
        }


class PerfBaselineDetailSchema(BaseSchema):
    unchangeable_fields = []

    def get_param_data(self):
        return {
            "baseline_id": {'type': int, 'required': True, 'example': '1', 'desc': '要展开的基线id'},
            "server_provider": {'type': str, 'required': True, 'example': 'aligroup',
                                'desc': '机器类型：aligroup/aliyun'},
            "test_suite_id": {'type': int, 'required': False, 'example': '56', 'desc': '要展开的test_suite_id'},
            "server_sm_name": {'type': str, 'required': False, 'example': '26H8JY1', 'desc': '集团机器展开：机型'},
            "server_instance_type": {'type': str, 'required': False, 'example': 'instance_type1',
                                     'desc': '云上机器展开：规格'},
            "test_case_id": {'type': int, 'required': False, 'example': '307', 'desc': '要展开的test_case_id'},
        }

    def get_delete_data(self):
        return {
            'id': {'type': int, 'required': True, 'example': '3', 'desc': '要删除性能详情的id'}
        }


class SearchBaselineSchema(BaseSchema):
    def get_param_data(self):
        return {
            'test_type': {'type': str, 'required': True, 'example': 'functional',
                          'desc': '测试类型（functional/performance）'},
            'server_provider': {'type': str, 'required': True,
                                'example': 'aligroup', 'desc': '机器类型（aligroup/aliyun）'},
            "search_baseline": {'type': str, 'required': True, 'example': '新', 'desc': '基线名称包含信息'},
        }


class SearchSuiteSchema(BaseSchema):
    def get_param_data(self):
        return {
            'baseline_id': {'type': int, 'required': True, 'example': "1", 'desc': '基线id'},
            'test_type': {'type': str, 'required': True, 'example': 'functional',
                          'desc': '测试类型（functional/performance）'},
            "search_suite": {'type': str, 'required': True, 'example': 'l', 'desc': 'suite名称包含信息'},
        }


class PerfBaselineAddOneSchema(BaseSchema):
    def get_body_data(self):
        return {
            'baseline_id': {'type': int, 'required': True, 'example': "3", 'desc': '基线id'},
            'job_id': {'type': int, 'required': True, 'example': '18', 'desc': '关联JOB ID'},
            "suite_id": {'type': int, 'required': True, 'example': '56', 'desc': '关联SUITE ID'},
            "case_id": {'type': int, 'required': True, 'example': '307', 'desc': '关联CASE ID'},
        }


class PerfBaselineBatchAddSchema(BaseSchema):
    def get_body_data(self):
        return {
            'baseline_id': {'type': int, 'required': True, 'example': "1", 'desc': '基线id'},
            'job_id': {'type': str, 'required': True, 'example': '13', 'desc': '关联JOB ID'},
            'suite_list': {'type': list, 'required': False, 'example': '[7, 8]   # TestSuite层批量加入',
                           'desc': 'TestSuite层批量加入的suite id的列表'},
            "suite_data": {'type': list, 'required': False,
                           'example': '''[
                               {                      # Testconf层批量加入
                                suite_id: 1,          # 展开的suite项的suite id
                                case_list: [1, 2, 3]  # 展开的suite项下的case id 列表
                               },
                               {
                                suite_id: 2,
                                case_list: [4, 5]
                               },
                               {
                                suite_id: 4,
                                case_list: [7]
                               },
                           ]''',
                           'desc': '批量加入需要的 suite名称包含信息,\nsuite_id（关联SUITE ID）下的case_id列表'},
        }


class ContrastBaselineSchema(BaseSchema):
    def get_body_data(self):
        return {
            'baseline_id': {'type': int, 'required': True, 'example': "3", 'desc': '基线id'},
            'job_id': {'type': int, 'required': True, 'example': '18', 'desc': '关联JOB ID'},
            "suite_id": {'type': int, 'required': True, 'example': '56', 'desc': '关联SUITE ID'},
            "case_id": {'type': int, 'required': True, 'example': '307', 'desc': '关联CASE ID'},
        }
