from tone.core.common.schemas import BaseSchema


class KernelSyncSchema(BaseSchema):

    def get_body_data(self):
        return {
            'version_list': {'type': list, 'required': True,
                             'example': "[4.19.91-20201103203001.g62342b22c.alios7.x86_64]",
                             'desc': '需要同步的内核版本名称的列表, 同步单个/多个内核（兼容）'},
        }
