from tone.core.common.schemas import BaseSchema


class WorkspaceSchema(BaseSchema):
    unchangeable_fields = ['name', 'is_approved']

    def get_param_data(self):
        return {
            'is_approved': {'type': bool, 'required': False, 'example': 'True', 'desc': '是否通过申请'},
            'is_public': {'type': bool, 'required': False, 'example': 'True', 'desc': '是否公开'},
            'scope': {'type': str, 'required': False, 'example': 'owner',
                      'desc': '1.owner:owner为我的ws列表, 2.creator:我创建的ws列表 3.join:我加入的ws列表)'},
        }

    def get_body_data(self):
        return {
            'name': {'type': str, 'required': True, 'example': 'kernel', 'desc': '名称'},
            'show_name': {'type': str, 'required': True, 'example': '内核测试', 'desc': '展示名称'},
            'description': {'type': str, 'required': False, 'example': '内核测试工作组', 'desc': '描述'},
            'is_approved': {'type': bool, 'required': True, 'example': True, 'desc': '是否通过申请'},
            'is_public': {'type': bool, 'required': True, 'example': True, 'desc': '是否公开'},
            'logo': {'type': str, 'required': False, 'example': 'oss://xxx.jpg', 'desc': 'logo图片'},
            'owner': {'type': int, 'required': False, 'example': 1, 'desc': 'owner id'}
        }

    def get_delete_data(self):
        return {
            'id': {'type': int, 'required': True, 'example': 2, 'desc': 'workspace id'},
            'reason': {'type': str, 'required': False, 'example': '不需要了', 'desc': '注销理由,超级用户注销可以不填'},
        }


class WorkspaceHistorySchema(BaseSchema):

    def get_param_data(self):
        return {
            'user_id': {'type': int, 'required': False, 'example': 1, 'desc': '用户id，默认为当前登陆用户id'},
        }

    def get_body_data(self):
        return {
            'ws_id': {'type': str, 'required': True, 'example': 't3ezpvwd', 'desc': '当前workspace id'},
        }


class WorkspaceMemberSchema(BaseSchema):

    def get_param_data(self):
        return {
            'ws_id': {'type': str, 'required': False, 'example': 't3ezpvwd', 'desc': 'workspace id'},
            'role': {'type': bool, 'required': False, 'example': 'admin', 'desc': '1.owner 2.admin（管理员）3.member(普通成员)'},
        }

    def get_body_data(self):
        return {
            'ws_id': {'type': str, 'required': True, 'example': 't3ezpvwd', 'desc': '当前workspace id'},
            'emp_id': {'type': str, 'required': False, 'example': 'WB607749',
                       'desc': '用户id(添加单个用户时)跟user_id_list二选一'},
            'emp_id_list': {'type': list, 'required': False, 'example': ['WB607749', ],
                            'desc': '用户id列表(批量添加用户时)，跟user_id二选一'},
            'is_admin': {'type': bool, 'required': True, 'example': False, 'desc': '是否是管理员'},
        }

    def get_update_data(self):
        return {
            'ws_id': {'type': str, 'required': True, 'example': 't3ezpvwd', 'desc': '当前workspace id'},
            'emp_id': {'type': str, 'required': False, 'example': 'WB607749',
                       'desc': '用户id(添加单个用户时)跟user_id_list二选一'},
            'emp_id_list': {'type': list, 'required': False, 'example': ['WB607749', ],
                            'desc': '用户id列表(批量添加用户时)，跟user_id二选一'},
            'is_admin': {'type': bool, 'required': True, 'example': False, 'desc': '是否是管理员'},
        }

    def get_delete_data(self):
        return {
            'ws_id': {'type': str, 'required': True, 'example': 't3ezpvwd', 'desc': '当前workspace id'},
            'user_id': {'type': int, 'required': False, 'example': 2, 'desc': '用户id(移除单个用户时)跟user_id_list二选一'},
            'user_id_list': {'type': list, 'required': False, 'example': [2, 3], 'desc': '用户id列表(批量删除用户时)，跟user_id二选一'},
        }


class ApproveSchema(BaseSchema):

    def get_param_data(self):
        return {
            'status': {'type': int, 'required': False, 'example': 0, 'desc': '0为待审核 1为已审核'},
            'object_type': {'type': str, 'required': False, 'example': 'workspace',
                            'desc': '默认workspace 后期会有权限相关'},
            'object_id': {'type': int, 'required': False, 'example': 2,
                          'desc': '对象id，如：object_type为workspace时，值为workspace id'},
            'action': {'type': str, 'required': False, 'example': 'join',
                       'desc': '默认查询ws申请列表，action为join时，查询人员申请列表'},
            'proposer': {'type': int, 'required': False, 'example': 2, 'desc': '申请人id'},
            'approver': {'type': int, 'required': False, 'example': 3, 'desc': '审批人id'},
        }

    def get_body_data(self):
        return {
            'id': {'type': int, 'required': True, 'example': 2, 'desc': '当前审批数据id'},
            'action': {'type': str, 'required': True, 'example': 'pass', 'desc': 'pass为通过  refuse为拒绝'},
            'reason': {'type': str, 'required': False, 'example': '再考虑一下', 'desc': '拒绝的时候需要注明理由'},
            'relation_data': {'type': dict, 'required': False, 'example': {'user_id': 1}, 'desc': '用户加入审批时需传该参数'},
        }


class WorkspaceApproveSchema(BaseSchema):
    def get_body_data(self):
        return {
            'ws_id': {'type': int, 'required': True, 'example': 2, 'desc': '当前workspace id'},
            'is_admin': {'type': bool, 'required': False, 'example': True, 'desc': '是否为管理员，默认为False'},
            'reason': {'type': str, 'required': True, 'example': '工作需要', 'desc': '申请理由'},
        }


class ApproveQuantitySchema(BaseSchema):
    def get_param_data(self):
        return {
            'ws_id': {'type': int, 'required': False, 'example': 2, 'desc': '当前workspace id  人员申请页数量统计的时候需要传该参数'},
            'action': {'type': str, 'required': False, 'example': 'join', 'desc': '默认不传，人员申请页数量统计的时候需要传该参数action=join'},
        }


class UploadSchema(BaseSchema):
    def get_body_data(self):
        return {
            'file_type': {'type': str, 'required': False, 'example': 'ws_logo', 'desc': '可以不传，默认ws_logo'},
            'file': {'type': str, 'required': True, 'example': 'file_obj', 'desc': 'file对象'},
        }


class MemberQuantitySchema(BaseSchema):
    def get_param_data(self):
        return {
            'scope': {'type': str, 'required': False, 'example': 'ws', 'desc': '默认ws'},
            'ws_id': {'type': int, 'required': False, 'example': 2, 'desc': 'workspace id'},
        }
