from tone.core.common.schemas import BaseSchema


class ServerTagSchema(BaseSchema):

    def get_param_data(self):
        return {
            'name': {'type': str, 'required': False, 'example': 'a', 'desc': '标签名称'},
            'description': {'type': str, 'required': False, 'example': 'a', 'desc': '备注'},
            'run_mode': {'type': str, 'required': False, 'example': 'aligroup',
                         'desc': '运行模式:standalone(单机), cluster(集群)'},
            'run_environment': {'type': str, 'required': False, 'example': 'standalone',
                                'desc': '运行环境:aligroup(集团), aliyun(云上)'},
            'ws_id': {'type': int, 'required': True, 'example': '1', 'desc': '关联Workspace'}
        }

    def get_body_data(self):
        return {
            'name': {'type': str, 'required': True, 'example': 'ltp-tpm_tools', 'desc': '名称'},
            'tag_color': {'type': str, 'required': True, 'example': '#88888', 'desc': '标签颜色'},
            'run_environment': {'type': str, 'required': True, 'example': 'standalone',
                                'desc': '运行环境:aligroup(集团), aliyun(云上)'},
            'run_mode': {'type': str, 'required': True, 'example': 'aligroup',
                         'desc': '运行模式:standalone(单机), cluster(集群)'},
            'description': {'type': str, 'required': False, 'example': 'abc', 'desc': '备注'},
            'ws_id': {'type': int, 'required': True, 'example': '1', 'desc': '关联Workspace'},
        }


class ServerTagDetailSchema(BaseSchema):

    def get_update_data(self):
        return {
            'name': {'type': str, 'required': True, 'example': 'ltp-tpm_tools', 'desc': '名称'},
            'description': {'type': str, 'required': False, 'example': 'abc', 'desc': '描述'}
        }


class TestServerCheckSchema(BaseSchema):
    def get_param_data(self):
        return {
            'ips': {'type': list, 'required': True, 'example': ['123.2.32.3', '1.1.1.1'],
                    'desc': 'ip/sn列表，逗号分隔;返回数据：success列表和errors列表'},
            'channel_type': {'type': str, 'required': True, 'example': 'staragent',
                             'desc': '控制通道：staragent，toneagent'}
        }


class TestServerChannelStateSchema(BaseSchema):
    def get_param_data(self):
        return {
            'ip': {'type': str, 'required': True, 'example': '123.2.32.3', 'desc': 'ip'},
            'channel_type': {'type': str, 'required': True, 'example': 'staragent',
                             'desc': '控制通道：staragent，toneagent'}
        }


class TestServerChannelCheckSchema(BaseSchema):
    def get_param_data(self):
        return {
            'ip': {'type': str, 'required': True, 'example': '123.2.32.3', 'desc': 'ip'},
            'channel_type': {'type': str, 'required': True, 'example': 'staragent',
                             'desc': '控制通道：staragent，toneagent'}
        }


class TestServerSchema(BaseSchema):

    def get_param_data(self):
        return {
            'ip': {'type': str, 'required': False, 'example': '1.1.1.1', 'desc': 'ip'},
            'sn': {'type': str, 'required': False, 'example': 'WSffws', 'desc': 'sn'},
            'description': {'type': str, 'required': False, 'example': 'aligroup', 'desc': '备注'},
            'device_type': {'type': list, 'required': False, 'example': 'phy_server',
                            'desc': '机器类型:phy_server(物理机), vm(虚拟机)'},
            'device_mode': {'type': str, 'required': False, 'example': 'abc', 'desc': '机型'},
            'channel_type': {'type': list, 'required': False, 'example': 'staragent',
                             'desc': '控制通道：staragent，toneagent'},
            'app_group': {'type': str, 'required': False, 'example': 'a', 'desc': '分组'},
            'state': {'type': list, 'required': False, 'example': 'Available',
                      'desc': '使用状态：Available, Occpuied, Broken, Reserved'},
            'tags': {'type': list, 'required': True, 'example': [11, 22, 333], 'desc': '标签ID数组'},
            'ws_id': {'type': int, 'required': True, 'example': '1', 'desc': '关联Workspace'}
        }

    def get_body_data(self):
        return {
            'ips': {'type': list, 'required': True, 'example': '[123.2.32.3,1.1.1.1]', 'desc': 'ip/sn数组'},
            'state': {'type': str, 'required': True, 'example': 'Available',
                      'desc': '使用状态：Available, Occpuied, Broken, Reserved'},
            'channel_type': {'type': list, 'required': False, 'example': 'staragent',
                             'desc': '控制通道：staragent，toneagent'},
            'tags': {'type': list, 'required': True, 'example': [11, 22, 333], 'desc': '标签ID数组'},
            'owner': {'type': int, 'required': True, 'example': '1', 'desc': 'owner'},
            'description': {'type': str, 'required': False, 'example': 'abc', 'desc': '备注'},
            'ws_id': {'type': int, 'required': True, 'example': '1', 'desc': '关联Workspace'}
        }


class TestServerDetailSchema(BaseSchema):
    def get_update_data(self):
        return {
            'name': {'type': str, 'required': True, 'example': 'WSffws', 'desc': '机器名称'},
            'channel_type': {'type': str, 'required': False, 'example': 'staragent',
                             'desc': '控制通道：staragent，toneagent'},
            'state': {'type': str, 'required': True, 'example': 'Available',
                      'desc': '使用状态：Available, Occpuied, Broken, Reserved'},
            'tags': {'type': list, 'required': True, 'example': [11, 22, 333], 'desc': '标签ID数组'},
            'owner': {'type': int, 'required': True, 'example': '1', 'desc': 'owner'},
            'description': {'type': str, 'required': False, 'example': 'abc', 'desc': '备注'}
        }


class TestServerUpdateSchema(BaseSchema):
    def get_param_data(self):
        return {
            'pk': {'type': str, 'required': True, 'example': 1, 'desc': '更新的机器id'}
        }


class TestServerBatchUpdateSchema(BaseSchema):
    def get_param_data(self):
        return {
            'pks': {'type': list, 'required': True, 'example': [1, 2, 3], 'desc': '更新的机器id数组'}
        }


class TestServerDeploySchema(BaseSchema):
    def get_body_data(self):
        return {
            'deploy_user': {'type': str, 'required': True, 'example': 'a', 'desc': '机器登录用户'},
            'deploy_pass': {'type': str, 'required': True, 'example': '123455', 'desc': '机器登录密码'},
            'server_id': {'type': int, 'required': True, 'example': '1', 'desc': '部署服务器id'}
        }


class TestClusterSchema(BaseSchema):
    def get_param_data(self):
        return {
            'name': {'type': str, 'required': False, 'example': 'a', 'desc': '集群名称'},
            'cluster_type': {'type': str, 'required': False, 'example': 'aligroup',
                             'desc': '集群类型:aligroup(集团), aliyun(云上)'},
            'owner': {'type': str, 'required': False, 'example': '1', 'desc': 'owner，支持多个查询'},
            'description': {'type': str, 'required': False, 'example': 'abc', 'desc': '描述'},
            'tags': {'type': list, 'required': True, 'example': [11, 22, 333], 'desc': '标签ID数组'},
            'ws_id': {'type': int, 'required': True, 'example': '1', 'desc': '关联Workspace'},
        }

    def get_body_data(self):
        return {
            'name': {'type': str, 'required': False, 'example': 'a', 'desc': '集群名称'},
            'cluster_type': {'type': str, 'required': True, 'example': 'aligroup',
                             'desc': '集群类型:aligroup(集团), aliyun(云上)'},
            'tags': {'type': list, 'required': True, 'example': [11, 22, 333], 'desc': '标签ID数组'},
            'owner': {'type': int, 'required': True, 'example': '1', 'desc': 'owner'},
            'ws_id': {'type': int, 'required': True, 'example': '1', 'desc': '关联Workspace'},
            'description': {'type': str, 'required': False, 'example': 'abc', 'desc': '备注'}
        }


class TestClusterDetailSchema(BaseSchema):
    def get_update_data(self):
        return {
            'name': {'type': str, 'required': False, 'example': 'a', 'desc': '集群名称'},
            'tags': {'type': list, 'required': True, 'example': [11, 22, 333], 'desc': '标签ID数组'},
            'owner': {'type': int, 'required': True, 'example': '1', 'desc': 'owner'},
            'description': {'type': str, 'required': False, 'example': 'abc', 'desc': '备注'}
        }


class TestClusterTestServerSchema(BaseSchema):
    def get_param_data(self):
        return {
            'cluster_id': {'type': int, 'required': False, 'example': 1, 'desc': '集群id'}
        }

    def get_body_data(self):
        return {
            'cluster_id': {'type': int, 'required': False, 'example': 1, 'desc': '集群id'},
            'ip': {'type': str, 'required': True, 'example': '123.2.32.3', 'desc': 'ip/sn'},
            'cluster_type': {'type': str, 'required': True, 'example': '11,22,333', 'desc': '集群类型：aligroup,aliyun'},
            'role': {'type': str, 'required': True, 'example': 'local', 'desc': 'local,remote'},
            'baseline_server': {'type': bool, 'required': True, 'example': 'True', 'desc': '是否基线'},
            'kernel_install': {'type': bool, 'required': True, 'example': 'True', 'desc': '是否安装内核'},
            'private_ip': {'type': str, 'required': True, 'example': '1.1.1.1', 'desc': '私有ip'},
            'var_name': {'type': str, 'required': False, 'example': 'abc', 'desc': '变量名称'},
            'owner': {'type': int, 'required': True, 'example': 1, 'desc': 'owner'},
            'ws_id': {'type': int, 'required': True, 'example': '1', 'desc': '关联Workspace'}
        }


class TestClusterCloudServerSchema(BaseSchema):
    def get_param_data(self):
        return {
            'cluster_id': {'type': int, 'required': False, 'example': 1, 'desc': '集群id'}
        }

    def get_body_data(self):
        return {
            'cluster_id': {'type': int, 'required': False, 'example': 1, 'desc': '集群id'},
            'role': {'type': str, 'required': True, 'example': 'local', 'desc': 'local,remote'},
            'baseline_server': {'type': bool, 'required': True, 'example': 'True', 'desc': '是否基线'},
            'kernel_install': {'type': bool, 'required': True, 'example': 'True', 'desc': '是否安装内核'},
            'private_ip': {'type': str, 'required': True, 'example': '1.1.1.1', 'desc': '私有ip'},
            'var_name': {'type': str, 'required': False, 'example': 'abc', 'desc': '变量名称'},
            'is_instance': {'type': bool, 'required': True, 'example': True, 'desc': '立即购买：False，选择已有：True'},
            'region': {'type': str, 'required': True, 'example': 'beijing', 'desc': 'region'},
            'zone': {'type': str, 'required': True, 'example': 'haidian', 'desc': 'zone'},
            'ak_id': {'type': int, 'required': True, 'example': '1', 'desc': 'ak_id'},
            'manufacturer': {'type': str, 'required': True, 'example': 'abc', 'desc': '云厂商'},
            'owner': {'type': int, 'required': True, 'example': '1', 'desc': 'owner'},
            'ws_id': {'type': str, 'required': True, 'example': '1', 'desc': '关联Workspace'},
            'instance_id': {'type': str, 'required': False, 'example': 'a', 'desc': '选择已有：实例id'},
            'name': {'type': str, 'required': True, 'example': 'a', 'desc': '选择已有：实例名称/配置名称'},
            'image': {'type': str, 'required': True, 'example': 'centos', 'desc': '立即购买：镜像'},
            'bandwidth': {'type': str, 'required': True, 'example': '100', 'desc': '立即购买：带宽'},
            'release_rule': {'type': bool, 'required': True, 'example': True, 'desc': '立即购买：用完释放'},
            'instance_type': {'type': str, 'required': True, 'example': '2C4G', 'desc': '立即购买：规格，只有ecs有规格，eci输入即可'},
            'storage_type': {'type': str, 'required': True, 'example': 'ssd', 'desc': '立即购买：数据盘类型'},
            'storage_size': {'type': str, 'required': True, 'example': '200', 'desc': '立即购买：数据盘大小'},
            'storage_number': {'type': str, 'required': True, 'example': '3', 'desc': '立即购买：数据盘个数'},
            'tags': {'type': list, 'required': True, 'example': [11, 22, 333], 'desc': '标签ID数组'},
            'description': {'type': str, 'required': False, 'example': 'cc', 'desc': '备注'}
        }


class TestClusterTestServerDetailSchema(BaseSchema):
    def get_update_data(self):
        return {
            'role': {'type': str, 'required': True, 'example': 'local', 'desc': 'local,remote'},
            'baseline_server': {'type': bool, 'required': True, 'example': 'True', 'desc': '是否基线'},
            'kernel_install': {'type': bool, 'required': True, 'example': 'True', 'desc': '是否安装内核'},
            'private_ip': {'type': str, 'required': True, 'example': '1.1.1.1', 'desc': '私有ip'},
            'var_name': {'type': str, 'required': False, 'example': 'abc', 'desc': '变量名称'},
            'channel_type': {'type': str, 'required': False, 'example': 'staragent',
                             'desc': '控制通道：staragent，toneagent'},
        }


class TestClusterCloudServerDetailSchema(BaseSchema):
    def get_update_data(self):
        return {
            'region': {'type': str, 'required': True, 'example': 'beijing', 'desc': '立即购买：region'},
            'zone': {'type': str, 'required': True, 'example': 'haidian', 'desc': '立即购买：zone'},
            'ak_id': {'type': int, 'required': True, 'example': '1', 'desc': '立即购买：ak_id'},
            'manufacturer': {'type': str, 'required': True, 'example': 'abc', 'desc': '立即购买：云厂商'},
            'template_name': {'type': str, 'required': True, 'example': 'a', 'desc': '立即购买：配置名称'},
            'image': {'type': str, 'required': True, 'example': 'centos', 'desc': '立即购买：镜像'},
            'bandwidth': {'type': str, 'required': True, 'example': '100', 'desc': '立即购买：带宽'},
            'release_rule': {'type': bool, 'required': True, 'example': True, 'desc': '立即购买：用完释放'},
            'instance_type': {'type': str, 'required': True, 'example': '2C4G', 'desc': '立即购买：规格'},
            'storage_type': {'type': str, 'required': True, 'example': 'ssd', 'desc': '立即购买：数据盘类型'},
            'storage_size': {'type': str, 'required': True, 'example': '200', 'desc': '立即购买：数据盘大小'},
            'storage_number': {'type': str, 'required': True, 'example': '3', 'desc': '立即购买：数据盘个数'},
            'owner': {'type': int, 'required': True, 'example': '1', 'desc': 'owner'},
            'tags': {'type': list, 'required': True, 'example': [11, 22, 333], 'desc': '标签ID数组'},
            'description': {'type': str, 'required': False, 'example': 'cc', 'desc': '备注'},
            'role': {'type': str, 'required': True, 'example': 'local', 'desc': 'local,remote'},
            'baseline_server': {'type': bool, 'required': True, 'example': 'True', 'desc': '是否基线'},
            'kernel_install': {'type': bool, 'required': True, 'example': 'True', 'desc': '是否安装内核'},
            'var_name': {'type': str, 'required': False, 'example': 'abc', 'desc': '变量名称'}
        }


class CloudServerSchema(BaseSchema):
    def get_param_data(self):
        return {
            'cluster_id': {'type': int, 'required': False, 'example': 1, 'desc': '集群id'},
            'tags': {'type': list, 'required': False, 'example': [1, 2], 'desc': '标签id数组'},
            'owner': {'type': list, 'required': False, 'example': [1, 2], 'desc': 'owner数组'},
            'is_instance': {'type': bool, 'required': False, 'example': True, 'desc': '实例：True，配置：False'},
            'server_conf': {'type': str, 'required': False, 'example': 'abc', 'desc': '机器配置，与上一字段配合'},
            'description': {'type': str, 'required': False, 'example': 'cc', 'desc': '备注'},
            'ws_id': {'type': int, 'required': True, 'example': '1', 'desc': '关联Workspace'}
        }

    def get_body_data(self):
        return {
            'is_instance': {'type': bool, 'required': True, 'example': True, 'desc': '立即购买：False，选择已有：True'},
            'region': {'type': str, 'required': True, 'example': 'beijing', 'desc': 'region'},
            'zone': {'type': str, 'required': True, 'example': 'haidian', 'desc': 'zone'},
            'ak_id': {'type': int, 'required': True, 'example': '1', 'desc': 'ak_id'},
            'manufacturer': {'type': str, 'required': True, 'example': 'abc', 'desc': '云厂商'},
            'owner': {'type': int, 'required': True, 'example': '1', 'desc': 'owner'},
            'ws_id': {'type': str, 'required': True, 'example': '1', 'desc': '关联Workspace'},
            'instance_id': {'type': str, 'required': False, 'example': 'a', 'desc': '选择已有：实例id'},
            'name': {'type': str, 'required': True, 'example': 'a', 'desc': '选择已有：实例名称/配置名称'},
            'image': {'type': str, 'required': True, 'example': 'centos', 'desc': '立即购买：镜像'},
            'bandwidth': {'type': str, 'required': True, 'example': '100', 'desc': '立即购买：带宽'},
            'release_rule': {'type': bool, 'required': True, 'example': True, 'desc': '立即购买：用完释放'},
            'instance_type': {'type': str, 'required': True, 'example': '2C4G', 'desc': '立即购买：规格，只有ecs有规格，eci输入即可'},
            'storage_type': {'type': str, 'required': True, 'example': 'ssd', 'desc': '立即购买：数据盘类型'},
            'storage_size': {'type': str, 'required': True, 'example': '200', 'desc': '立即购买：数据盘大小'},
            'storage_number': {'type': str, 'required': True, 'example': '3', 'desc': '立即购买：数据盘个数'},
            'tags': {'type': list, 'required': True, 'example': [11, 22, 333], 'desc': '标签ID数组'},
            'description': {'type': str, 'required': False, 'example': 'cc', 'desc': '备注'}
        }


class CloudServerDetailSchema(BaseSchema):
    def get_update_data(self):
        return {
            'region': {'type': str, 'required': True, 'example': 'beijing', 'desc': '立即购买：region'},
            'zone': {'type': str, 'required': True, 'example': 'haidian', 'desc': '立即购买：zone'},
            'ak_id': {'type': int, 'required': True, 'example': '1', 'desc': '立即购买：ak_id'},
            'manufacturer': {'type': str, 'required': True, 'example': 'abc', 'desc': '立即购买：云厂商'},
            'template_name': {'type': str, 'required': True, 'example': 'a', 'desc': '立即购买：配置名称'},
            'image': {'type': str, 'required': True, 'example': 'centos', 'desc': '立即购买：镜像'},
            'bandwidth': {'type': str, 'required': True, 'example': '100', 'desc': '立即购买：带宽'},
            'release_rule': {'type': bool, 'required': True, 'example': True, 'desc': '立即购买：用完释放'},
            'instance_type': {'type': str, 'required': True, 'example': '2C4G', 'desc': '立即购买：规格'},
            'storage_type': {'type': str, 'required': True, 'example': 'ssd', 'desc': '立即购买：数据盘类型'},
            'storage_size': {'type': str, 'required': True, 'example': '200', 'desc': '立即购买：数据盘大小'},
            'storage_number': {'type': str, 'required': True, 'example': '3', 'desc': '立即购买：数据盘个数'},
            'owner': {'type': int, 'required': True, 'example': '1', 'desc': 'owner'},
            'tags': {'type': list, 'required': True, 'example': [11, 22, 333], 'desc': '标签ID数组'},
            'description': {'type': str, 'required': False, 'example': 'cc', 'desc': '备注'}
        }


class CloudAkSchema(BaseSchema):
    def get_param_data(self):
        return {
            'ws_id': {'type': str, 'required': True, 'example': 'abc', 'desc': '关联Workspace查询'},
            "name": {'type': str, 'required': False, 'example': 'ak名称', 'desc': 'ak名称查询(包含)'},
            "provider": {'type': list, 'required': False, 'example': '[aliyun_eci]',
                         'desc': '提供商 aliyun_ecs: 阿里云ECS,aliyun_eci: 阿里云ECI, 查询'},
            "id": {'type': int, 'required': False, 'example': '1', 'desc': 'ak 的id查询'},
            "access_id": {'type': str, 'required': False, 'example': 'key', 'desc': 'access_id'},
            "access_key": {'type': str, 'required': False, 'example': 'secret',
                           'desc': 'access_key'},
            "enable": {'type': bool, 'required': False, 'example': True, 'desc': '是否启用'},
            "creator": {'type': list, 'required': False, 'example': '[1]', 'desc': '创建者id列表'},
            "update_user": {'type': list, 'required': False, 'example': '[1]', 'desc': '修改者id列表'},
            "gmt_created": {'type': str, 'required': False, 'example': '-gmt_created', 'desc': '创建时间升序+,（-降序）'},
            "gmt_modified": {'type': str, 'required': False, 'example': '-gmt_modified', 'desc': '修改时间升序+,（-降序）'},
        }

    def get_body_data(self):
        return {
            "name": {'type': str, 'required': True, 'example': 'ak名称', 'desc': 'ak名称'},
            "provider": {'type': str, 'required': True, 'example': 'aliyun_eci',
                         'desc': '提供商 aliyun_ecs: 阿里云ECS,aliyun_eci: 阿里云ECI'},
            "access_id": {'type': str, 'required': True, 'example': 'key', 'desc': 'access_id'},
            "access_key": {'type': str, 'required': True, 'example': 'secret',
                           'desc': 'access_key'},
            "ws_id": {'type': str, 'required': True, 'example': 'axiwxl9p', 'desc': '关联Workspace'},
            "enable": {'type': bool, 'required': True, 'example': True, 'desc': '是否启用'},
            "description": {'type': str, 'required': False, 'example': 'aliyun_eci', 'desc': '描述'},
        }

    def get_update_data(self):
        return {
            "id": {'type': int, 'required': True, 'example': '1', 'desc': 'ak 的id'},
            "name": {'type': str, 'required': True, 'example': 'ak名称', 'desc': 'ak名称'},
            "provider": {'type': str, 'required': True, 'example': 'aliyun_eci',
                         'desc': '提供商 aliyun_ecs: 阿里云ECS,aliyun_eci: 阿里云ECI'},
            "ws_id": {'type': str, 'required': True, 'example': 'axiwxl9p', 'desc': '关联Workspace'},
            "access_id": {'type': str, 'required': False, 'example': 'key', 'desc': 'access_id'},
            "access_key": {'type': str, 'required': False, 'example': 'secret',
                           'desc': 'access_key'},
            "enable": {'type': bool, 'required': True, 'example': True, 'desc': '是否启用'},
            "description": {'type': str, 'required': False, 'example': 'aliyun_eci', 'desc': '关联Workspace'},
        }

    def get_delete_data(self):
        return {
            "id_list": {'type': list, 'required': True, 'example': '[1, 2, 3]', 'desc': '要删除的ak 的id列表'},
        }


class CloudImageSchema(BaseSchema):
    def get_param_data(self):
        return {
            'ws_id': {'type': str, 'required': True, 'example': 'abc', 'desc': '关联Workspace查询'},
            'ak_id': {'type': list, 'required': False, 'example': '[1]', 'desc': 'ak_id的列表'},
            'region': {'type': str, 'required': False, 'example': 'cn-hangzhou', 'desc': 'region'},
            "provider": {'type': list, 'required': False, 'example': '[aliyun_eci]',
                         'desc': '提供商 aliyun_ecs: 阿里云ECS,aliyun_eci: 阿里云ECI'},
            "image_id": {'type': str, 'required': False, 'example': 'redis', 'desc': 'image_id'},
            "image_name": {'type': str, 'required': False, 'example': 'redis', 'desc': '镜像名称'},
            "image_version": {'type': str, 'required': False, 'example': '', 'desc': 'image版本信息'},
            "platform": {'type': str, 'required': False, 'example': 'CentOS', 'desc': '发行商 CentOS, Ubuntu等'},
            "creator": {'type': list, 'required': False, 'example': '[1]', 'desc': '创建者id列表'},
            "update_user": {'type': list, 'required': False, 'example': '[1]', 'desc': '修改者id列表'},
            "gmt_created": {'type': str, 'required': False, 'example': '-gmt_created', 'desc': '创建时间升序+,（-降序）'},
            "gmt_modified": {'type': str, 'required': False, 'example': '-gmt_modified', 'desc': '修改时间升序+,（-降序）'},
        }

    def get_body_data(self):
        return {
            'ws_id': {'type': str, 'required': True, 'example': 'abc', 'desc': '关联Workspace'},
            "ak_id": {'type': int, 'required': True, 'example': '5', 'desc': 'ak id通过发送ak查询请求获取列表'},
            "provider": {'type': str, 'required': True, 'example': 'aliyun_eci',
                         'desc': '提供商 aliyun_ecs: 阿里云ECS,aliyun_eci: 阿里云ECI'},
            "region": {'type': str, 'required': True, 'example': 'cn-beijing', 'desc': 'region/location id'},
            "image_id": {'type': str, 'required': True, 'example': 'redis', 'desc': 'image_id'},
            "image_name": {'type': str, 'required': True, 'example': 'redis', 'desc': '镜像名称'},
            "image_version": {'type': str, 'required': False, 'example': '', 'desc': 'image版本信息'},
            "platform": {'type': str, 'required': False, 'example': 'CentOS', 'desc': '发行商 CentOS, Ubuntu等'},
        }

    def get_update_data(self):
        return {
            'id': {'type': int, 'required': True, 'example': '5', 'desc': '要修改的image的id'},
            "ak_id": {'type': int, 'required': True, 'example': '5', 'desc': 'ak的 id'},
            "provider": {'type': str, 'required': True, 'example': 'aliyun_eci',
                         'desc': '提供商 aliyun_ecs: 阿里云ECS,aliyun_eci: 阿里云ECI'},
            "region": {'type': str, 'required': True, 'example': 'cn-beijing', 'desc': 'region/location id'},
            "image_id": {'type': str, 'required': False, 'example': 'redis', 'desc': 'image_id'},
            "image_name": {'type': str, 'required': False, 'example': 'redis', 'desc': '镜像名称'},
            "image_version": {'type': str, 'required': False, 'example': '', 'desc': 'image版本信息'},
            "platform": {'type': str, 'required': False, 'example': 'CentOS', 'desc': '发行商 CentOS, Ubuntu等'},
        }

    def get_delete_data(self):
        return {
            "id_list": {'type': list, 'required': True, 'example': '[1, 2, 3]', 'desc': '要删除的image 的id列表'},
        }


class CloudServerImageSchema(BaseSchema):
    def get_param_data(self):
        return {
            'ak_id': {'type': int, 'required': True, 'example': '1', 'desc': 'ak_id'},
            'region': {'type': str, 'required': True, 'example': 'cn-hangzhou', 'desc': 'region'},
            'zone': {'type': str, 'required': True, 'example': 'cn-hangzhou-b', 'desc': 'zone'}
        }


class CloudServerInstanceSchema(BaseSchema):
    def get_param_data(self):
        return {
            'ak_id': {'type': int, 'required': True, 'example': '1', 'desc': 'ak_id'},
            'region': {'type': str, 'required': True, 'example': 'cn-hangzhou', 'desc': 'region'},
            'zone': {'type': str, 'required': True, 'example': 'cn-hangzhou-b', 'desc': 'zone'}
        }


class CloudServerInstanceTypeSchema(BaseSchema):
    def get_param_data(self):
        return {
            'ak_id': {'type': int, 'required': True, 'example': '1', 'desc': 'ak_id'},
            'region': {'type': str, 'required': True, 'example': 'cn-hangzhou', 'desc': 'region'},
            'zone': {'type': str, 'required': True, 'example': 'cn-hangzhou-b', 'desc': 'zone'}
        }


class CloudServerRegionSchema(BaseSchema):
    def get_param_data(self):
        return {
            'ak_id': {'type': int, 'required': True, 'example': '1', 'desc': 'ak_id'}
        }


class CloudServerZoneSchema(BaseSchema):
    def get_param_data(self):
        return {
            'ak_id': {'type': int, 'required': True, 'example': '1', 'desc': 'ak_id'},
            'region': {'type': str, 'required': True, 'example': 'cn-hangzhou', 'desc': 'region'}
        }


class CloudServerDiskCategoriesSchema(BaseSchema):
    def get_param_data(self):
        return {
            'ak_id': {'type': int, 'required': True, 'example': '1', 'desc': 'ak_id'},
            'region': {'type': str, 'required': True, 'example': 'cn-hangzhou', 'desc': 'region'},
            'zone': {'type': str, 'required': True, 'example': 'cn-hangzhou-b', 'desc': 'zone'}
        }


class HelpDocSchema(BaseSchema):
    def get_param_data(self):
        return {
            "id": {'type': int, 'required': False, 'example': '1', 'desc': '需要查询文档的id'},
            "title": {'type': str, 'required': False, 'example': '帮助', 'desc': '要查询的标题信息'},
        }

    def get_body_data(self):
        return {
            "title": {'type': str, 'required': True, 'example': True, 'desc': '文档标题'},
            "order_id": {'type': int, 'required': False, 'example': 1, 'desc': '显示顺序的id'},
            "content": {'type': str, 'required': False, 'example': '文档内容', 'desc': '文档信息'},
        }

    def get_update_data(self):
        return {
            "id": {'type': int, 'required': True, 'example': '1', 'desc': '要修改帮助文档的id'},
            "order_id": {'type': int, 'required': False, 'example': 1, 'desc': '显示顺序的id'},
            "title": {'type': str, 'required': False, 'example': True, 'desc': '文档标题'},
            "content": {'type': str, 'required': False, 'example': '文档内容', 'desc': '修改后的文档信息'},
        }

    def get_delete_data(self):
        return {
            "id": {'type': int, 'required': True, 'example': '1', 'desc': '要删除帮助文档的id'},
        }


class TestFarmSchema(BaseSchema):
    def get_param_data(self):
        return {
            "is_major": {'type': bool, 'required': False, 'example': 'True', 'desc': '是否主站点'},
            "site_url": {'type': str, 'required': False, 'example': '帮助', 'desc': 'Testfarm地址'},
        }

    def get_body_data(self):
        return {
            "site_id": {'type': int, 'required': False, 'example': '1', 'desc': '修改的站点id'},
            "is_major": {'type': bool, 'required': False, 'example': 'True', 'desc': '是否主站点'},
            "site_url": {'type': str, 'required': False, 'example': '帮助', 'desc': 'Testfarm地址'},
            "site_token": {'type': str, 'required': False, 'example': '文档内容', 'desc': 'Testfarm Token'},
            "push_config_data": {'type': list, 'required': True, 'example': '[[ws_id, project_id, job_name_rule], ...]',
                                 'desc': '推送信息列表'},
        }
