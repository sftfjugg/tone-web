from tone.core.common.schemas import BaseSchema


class TestCaseSchema(BaseSchema):

    def get_param_data(self):
        return {
            'suite_id': {'type': int, 'required': False, 'example': '1', 'desc': '根据suite查询'},
            'case_id': {'type': int, 'required': False, 'example': '1', 'desc': '根据case查询'},
            'name': {'type': str, 'required': False, 'example': 'lkp', 'desc': 'name'}
        }

    def get_body_data(self):
        return {
            'name': {'type': str, 'required': True, 'example': 'ltp-tpm_tools', 'desc': '名称'},
            'test_suite_id': {'type': int, 'required': True, 'example': '2', 'desc': 'suite_id'},
            'repeat': {'type': int, 'required': True, 'example': '1', 'desc': '执行次数'},
            'timeout': {'type': int, 'required': True, 'example': '10800', 'desc': '超时时间'},
            'domain': {'type': int, 'required': True, 'example': 1, 'desc': 'domain_id'},
            'domain_name': {'type': int, 'required': True, 'example': 1, 'desc': 'domain_name'},
            'doc': {'type': str, 'required': False, 'example': 'abc', 'desc': '文档'},
            'description': {'type': str, 'required': False, 'example': 'abc', 'desc': '描述'},
            'var': {'type': str, 'required': False, 'example': '{}', 'desc': '变量json数据'},
            'is_default': {'type': bool, 'required': False, 'example': '0', 'desc': '是否默认'}
        }


class TestCaseDetailSchema(BaseSchema):

    def get_update_data(self):
        return {
            'name': {'type': str, 'required': True, 'example': 'ltp-tpm_tools', 'desc': '名称'},
            'test_suite_id': {'type': int, 'required': True, 'example': '2', 'desc': 'suite_id'},
            'repeat': {'type': int, 'required': True, 'example': '1', 'desc': '执行次数'},
            'timeout': {'type': int, 'required': True, 'example': '10800', 'desc': '超时时间'},
            'domain': {'type': int, 'required': True, 'example': 1, 'desc': '领域id'},
            'doc': {'type': str, 'required': False, 'example': 'abc', 'desc': '文档'},
            'description': {'type': str, 'required': False, 'example': 'abc', 'desc': '描述'},
            'var': {'type': str, 'required': False, 'example': '{}', 'desc': '变量json数据'},
            'is_default': {'type': bool, 'required': False, 'example': '0', 'desc': '是否默认'}
        }


class TestCaseBatchSchema(BaseSchema):

    def get_update_data(self):
        return {
            'case_id_list': {'type': str, 'required': False, 'example': '4,5,6', 'desc': '批量修改的case_id'},
            'case_id': {'type': int, 'required': False, 'example': '4', 'desc': '单个修改的case_id，和上一个参数互斥'},
            'domain': {'type': int, 'required': True, 'example': '3', 'desc': '领域id'},
            'timeout': {'type': int, 'required': True, 'example': '100', 'desc': '超时时间'},
            'repeat': {'type': int, 'required': True, 'example': '10', 'desc': '执行次数'}
        }

    def get_delete_data(self):
        return {
            'id_list': {'type': str, 'required': False, 'example': '1,2,3', 'desc': '批量删除id'}
        }


class TestSuiteSchema(BaseSchema):
    def get_param_data(self):
        return {
            'suite_id': {'type': int, 'required': False, 'example': '4', 'desc': 'suite_id'},
            'test_type': {'type': str, 'required': False, 'example': 'functional',
                          'desc': '测试类型: (functional, 功能测试;performance, 性能测试;business, 业务测试;stability, 稳定性测试)'},
            'run_mode': {'type': str, 'required': False, 'example': 'standalone',
                         'desc': '运行模式:standalone,cluster'},
            'domain': {'type': str, 'required': False, 'example': '3,4',
                       'desc': '多选，领域:(1, 内存;2, 调度;3, cpu;4, 文件系统;5, IO子系统;6, 网络;7, Pounch;8, 其他)'},
            'name': {'type': str, 'required': False, 'example': 'lkp', 'desc': '根据name模糊查询suite列表'},
            'order': {'type': str, 'required': False, 'example': 'gmt_created', 'desc': 'gmt_created/-gmt_created'},
            'owner': {'type': str, 'required': False, 'example': '1,2,3', 'desc': '根据owner筛选suite列表'},
            'scope': {'type': str, 'required': False, 'example': 'case', 'desc': '如果为case查询列表带test_case_list'}
        }

    def get_body_data(self):
        return {
            'name': {'type': str, 'required': True, 'example': 'ltp-tpm_tools', 'desc': '名称'},
            'test_type': {'type': str, 'required': True, 'example': 'functional', 'desc': '测试类型'},
            'run_mode': {'type': str, 'required': True, 'example': 'standalone',
                         'desc': '运行模式:standalone,cluster'},
            'domain': {'type': int, 'required': True, 'example': 1, 'desc': 'domain_id'},
            'domain_name': {'type': int, 'required': True, 'example': 1, 'desc': 'domain_name'},
            'doc': {'type': str, 'required': False, 'example': 'abc', 'desc': '文档'},
            'description': {'type': str, 'required': False, 'example': 'abc', 'desc': '描述'},
            'owner': {'type': int, 'required': True, 'example': '4', 'desc': 'Owner'},
            'is_default': {'type': bool, 'required': False, 'example': '0', 'desc': '是否默认'}
        }


class TestSuiteDetailSchema(BaseSchema):

    def get_update_data(self):
        return {
            'name': {'type': str, 'required': True, 'example': 'ltp-tpm_tools', 'desc': '名称'},
            'test_type': {'type': str, 'required': True, 'example': 'functional', 'desc': '测试类型'},
            'run_mode': {'type': str, 'required': True, 'example': 'standalone', 'desc': '运行模式'},
            'domain': {'type': int, 'required': True, 'example': '3', 'desc': '领域'},
            'doc': {'type': str, 'required': False, 'example': 'abc', 'desc': '文档'},
            'description': {'type': str, 'required': False, 'example': 'abc', 'desc': '描述'},
            'owner': {'type': int, 'required': True, 'example': '4', 'desc': 'Owner'},
            'is_default': {'type': bool, 'required': False, 'example': '0', 'desc': '是否默认'}
        }


class TestSuiteExistSchema(BaseSchema):
    def get_param_data(self):
        return {
            'suite_name': {'type': str, 'required': False, 'example': 'ltp', 'desc': 'suite_name'},
            'test_type': {'type': str, 'required': False, 'example': 'functional', 'desc': 'functional/performance'}
        }


class TestMetricSchema(BaseSchema):

    def get_param_data(self):
        return {
            'suite_id': {'type': int, 'required': False, 'example': '4', 'desc': 'suite_id'},
            'case_id': {'type': int, 'required': False, 'example': '4', 'desc': 'case_id与上一参数互斥'}
        }

    def get_body_data(self):
        return {
            'name': {'type': list, 'required': True, 'example': '["score","score1","score2"]', 'desc': '指标名，支持批量添加'},
            'object_type': {'type': str, 'required': True, 'example': 'suite', 'desc': 'suite/case'},
            'object_id': {'type': int, 'required': True, 'example': '4', 'desc': 'suite_id/case_id'},
            'cv_threshold': {'type': float, 'required': True, 'example': '25145', 'desc': '变异系数阈值'},
            'cmp_threshold': {'type': float, 'required': True, 'example': '102214', 'desc': '指标跟基线的对比的阈值'},
            'direction': {'type': str, 'required': True, 'example': 'decline', 'desc': '方向:decline,下降；increase，上升'},
            'is_sync': {'type': bool, 'required': True, 'example': '0', 'desc': '是否同步到conf'}
        }


class TestMetricDetailSchema(BaseSchema):

    def get_update_data(self):
        return {
            'name': {'type': str, 'required': True, 'example': 'score', 'desc': '指标名'},
            'object_type': {'type': str, 'required': True, 'example': 'suite', 'desc': 'suite/case'},
            'object_id': {'type': int, 'required': True, 'example': '4', 'desc': 'suite_id/case_id'},
            'cv_threshold': {'type': float, 'required': True, 'example': '25145', 'desc': '变异系数阈值'},
            'cmp_threshold': {'type': float, 'required': True, 'example': '102214', 'desc': '指标跟基线的对比的阈值'},
            'direction': {'type': int, 'required': True, 'example': '0', 'desc': '方向'},
            'is_sync': {'type': bool, 'required': True, 'example': '0', 'desc': '是否同步到conf'}
        }

    def get_delete_data(self):
        return {
            'id': {'type': int, 'required': True, 'example': 23, 'desc': 'metric id'},
            'name': {'type': str, 'required': True, 'example': 'score', 'desc': '指标名'},
            'object_type': {'type': str, 'required': True, 'example': 'suite', 'desc': 'suite/case'},
            'object_id': {'type': int, 'required': True, 'example': '4', 'desc': 'suite_id/case_id'},
            'is_sync': {'type': bool, 'required': True, 'example': '0', 'desc': '是否同步到conf'}
        }


class WorkspaceCaseSchema(BaseSchema):
    def get_param_data(self):
        return {
            'ws_id': {'type': int, 'required': True, 'example': '1', 'desc': '查询ws下suite列表'},
            'suite_id': {'type': int, 'required': False, 'example': '1', 'desc': '根据suite查询case列表'},
            'object_type': {'type': str, 'required': False, 'example': 'suite', 'desc': '查询ws下suite/case中的metric'},
            'object_id': {'type': str, 'required': False, 'example': '1', 'desc': 'suite_id/case_id,与上一参数配合使用'},
            'test_type': {'type': str, 'required': False, 'example': 'functional',
                          'desc': '测试类型: (functional, 功能测试;performance, 性能测试;business, 业务测试;stability, 稳定性测试)'},
            'run_mode': {'type': str, 'required': False, 'example': 'standalone',
                         'desc': '运行模式:standalone,cluster'},
            'domain': {'type': str, 'required': False, 'example': '3,4',
                       'desc': '多选，领域:(1, 内存;2, 调度;3, cpu;4, 文件系统;5, IO子系统;6, 网络;7, Pounch;8, 其他)'},
            'name': {'type': str, 'required': False, 'example': 'lkp', 'desc': '根据name模糊查询suite列表'},
            'order': {'type': str, 'required': False, 'example': 'gmt_created', 'desc': 'gmt_created/-gmt_created'},
            'owner': {'type': str, 'required': False, 'example': '1,2,3', 'desc': '根据owner筛选suite列表'}
        }

    def get_body_data(self):
        return {
            'test_type': {'type': str, 'required': True, 'example': 'performance',
                          'desc': '测试类型(functional/performance/business/stability)'},
            'test_suite_id': {'type': int, 'required': True, 'example': '1', 'desc': '关联Suite'},
            'test_case_id': {'type': int, 'required': True, 'example': '4', 'desc': '关联Case'},
            'ws_id': {'type': str, 'required': True, 'example': '1', 'desc': '关联Workspace'}
        }


class WorkspaceCaseBatchSchema(BaseSchema):

    def get_body_data(self):
        return {
            'test_type': {'type': str, 'required': True, 'example': 'performance',
                          'desc': '测试类型(functional/performance/business/stability)'},
            'suite_id_list': {'type': str, 'required': False, 'example': '1,2,3', 'desc': '根据suite批量添加case_id'},
            'case_id_list': {'type': str, 'required': False, 'example': '1,2,3', 'desc': '批量添加case_id'},
            'case_id': {'type': int, 'required': False, 'example': '1', 'desc': '单条添加case_id，和上一参数互斥'},
            'ws_id': {'type': str, 'required': True, 'example': '1', 'desc': '关联Workspace'}
        }

    def get_delete_data(self):
        return {
            'id_list': {'type': str, 'required': False, 'example': '1,2,3', 'desc': '批量删除id'},
            'id': {'type': int, 'required': False, 'example': '1', 'desc': '单条删除，和上一参数互斥'},
            'ws_id': {'type': str, 'required': True, 'example': '1', 'desc': '关联Workspace'}
        }


class DomainSchema(BaseSchema):

    def get_param_data(self):
        return {
            'id': {'type': int, 'required': False, 'example': '5', 'desc': '根据domain的id搜索'},
            'name': {'type': str, 'required': False, 'example': '内存', 'desc': '根据domain名称搜索'},
            "creator": {'type': list, 'required': False, 'example': '[1]', 'desc': '创建者id列表'},
            "update_user": {'type': list, 'required': False, 'example': '[1]', 'desc': '修改者id列表'},
            "gmt_created": {'type': str, 'required': False, 'example': '-gmt_created', 'desc': '创建时间升序+,（-降序）'},
            "gmt_modified": {'type': str, 'required': False, 'example': '-gmt_modified', 'desc': '修改时间升序+,（-降序）'},
        }

    def get_body_data(self):
        return {
            'name': {'type': str, 'required': True, 'example': 'other', 'desc': '新增domain的名称'},
            'description': {'type': str, 'required': False, 'example': '其他', 'desc': '描述'},
        }

    def get_update_data(self):
        return {
            'id': {'type': int, 'required': True, 'example': '5', 'desc': '修改domain的id'},
            'name': {'type': str, 'required': True, 'example': '内存2', 'desc': '修改后的domain名称'},
            'description': {'type': str, 'required': False, 'example': 'memory2', 'desc': '描述'}
        }

    def get_delete_data(self):
        return {
            'id_list': {'type': list, 'required': True, 'example': '[11, 12, 13]', 'desc': '删除domain的id数组'},
        }


class SuiteRetrieveSchema(BaseSchema):
    def get_param_data(self):
        return {
            'total_num': {'type': bool, 'required': False, 'example': 'true', 'desc': '1. 获取性能测试、功能测试数量,标识'},
            'ws_id': {'type': str, 'required': False, 'example': 'ah9m9or5', 'desc': '2. 获取性能/功能下suite列表,工作台id'},
            "test_type": {'type': str, 'required': False, 'example': 'functional',
                          'desc': '测试类型：functional/performance'},
            "suite_id": {'type': int, 'required': False, 'example': '45', 'desc': '3. 获取 suite下conf 列表'},
            "case_id": {'type': int, 'required': False, 'example': '569', 'desc': '4.获取case同级conf列表'},
        }

    def get_body_data(self):
        return {
            'search_key': {'type': str, 'required': True, 'example': 'unixbench-300s', 'desc': '搜索信息'},
        }
