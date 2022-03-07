from tone.core.common.schemas import BaseSchema


class OfflineDataUploadSchema(BaseSchema):
    def get_param_data(self):
        return {
            'id': {'type': int, 'required': False, 'example': '1', 'desc': '根据id查询'},
            'ws_id': {'type': str, 'required': False, 'example': '1', 'desc': '根据ws_id查询列表'},
            'name': {'type': str, 'required': False, 'example': 'lkp', 'desc': 'name'}
        }

    def get_body_data(self):
        return {
            'file': {'type': str, 'required': True, 'example': '1', 'desc': 'form-data上传文件'},
            'project_id': {'type': int, 'required': True, 'example': '1', 'desc': '项目id'},
            'baseline_id': {'type': int, 'required': True, 'example': '2', 'desc': '基线id'},
            'job_type_id': {'type': int, 'required': True, 'example': '2', 'desc': 'job type id'},
            'test_type': {'type': str, 'required': True, 'example': 'functional',
                          'desc': '功能类型：functional，性能测试：performance'},
            'server_type': {'type': str, 'required': True, 'example': 'aliyun', 'desc': 'aligroup，aliyun'},
            'ws_id': {'type': str, 'required': True, 'example': '2313', 'desc': 'workspace id'}
        }

    def get_delete_data(self):
        return {
            'pk': {'type': int, 'required': True, 'example': '1', 'desc': '删除id'}
        }
