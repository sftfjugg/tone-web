from tone.core.common.schemas import BaseSchema


class UserSchema(BaseSchema):
    unchangeable_fields = []

    def get_body_data(self):
        return {
            'user_id': {'type': int, 'required': True, 'example': 1, 'desc': '用户id'},
            'role_id_list': {'type': list, 'required': True, 'example': [1, 2], 'desc': '角色id 数组'},
        }
