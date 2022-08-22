from django.db import models
from django_extensions.db.fields import json

from tone.core.common.enums.ts_enums import TestServerEnums

from tone.models.base.base_models import BaseModel


class TestServer(BaseModel):
    name = models.CharField(max_length=255, help_text='机器名称')
    ip = models.CharField(max_length=64, help_text='IP')
    sn = models.CharField(max_length=64, help_text='SN', null=True, blank=True)
    tsn = models.CharField(max_length=64, help_text='TSN', null=True, blank=True)
    hostname = models.CharField(max_length=64, help_text='Host Name')
    # 逻辑
    app_group = models.CharField(max_length=64, help_text='APP GROUP')
    app_state = models.CharField(max_length=64, help_text='应用状态')
    security_domain = models.CharField(max_length=64, help_text='安全域')
    idc = models.CharField(max_length=64, help_text='IDC')
    parent_server_id = models.IntegerField(null=True, blank=True, help_text='父机器')
    # 硬件型号
    manufacturer = models.CharField(max_length=64, help_text='供应商')
    device_type = models.CharField(max_length=64, choices=TestServerEnums.DEVICE_TYPE_CHOICES, help_text='机器类型')
    device_mode = models.CharField(max_length=64, help_text='型号')
    sm_name = models.CharField(max_length=64, help_text='机型')
    # 硬件配置
    arch = models.CharField(max_length=64, help_text='ARCH')
    cpu = models.CharField(max_length=64, help_text='CPU')
    memory = models.CharField(max_length=64, help_text='内存')
    storage = models.CharField(max_length=64, help_text='存储磁盘')
    cpu_device = models.CharField(max_length=64, help_text='CPU类型')
    memory_device = models.CharField(max_length=64, help_text='内存类型')
    network = models.CharField(max_length=64, help_text='网络')
    net_device = models.CharField(max_length=64, help_text='网络类型')
    # 软件
    kernel = models.CharField(max_length=64, help_text='内核')
    platform = models.CharField(max_length=64, help_text='平台')
    uname = models.CharField(max_length=64, help_text='UName')
    #
    state = models.CharField(max_length=64, choices=TestServerEnums.SERVER_STATE_CHOICES, default='Available',
                             help_text='状态')
    real_state = models.CharField(max_length=64, choices=TestServerEnums.SERVER_STATE_CHOICES, default='Available',
                                  help_text='真实状态')
    history_state = models.CharField(max_length=64, choices=TestServerEnums.SERVER_STATE_CHOICES, default='Available',
                                     help_text='历史状态')
    check_state_time = models.DateTimeField(null=True, help_text='最近一次检测机器真实状态的时间')
    # state=1 use_type:平台或者用户手动reserve
    use_type = models.CharField(max_length=64, choices=TestServerEnums.USE_TYPE_CHOICES, help_text='Reserve类型')
    description = models.CharField(max_length=64, help_text='描述')

    channel_type = models.CharField(max_length=64, choices=TestServerEnums.SERVER_CHANNEL_TYPE_CHOICES,
                                    help_text='通道类型')
    channel_state = models.BooleanField(default=False, help_text='控制通道状态，是否部署完成')
    private_ip = models.CharField(max_length=64, help_text='私有IP')
    owner = models.IntegerField(null=True, help_text='Owner')
    ws_id = models.CharField(max_length=8, db_index=True, help_text='关联Workspace')
    # 机器管理只展示单机池中的机器
    in_pool = models.BooleanField(default=True, help_text='是否在单机池中')

    console_type = models.CharField(max_length=64, help_text='console类型')
    console_conf = models.CharField(max_length=64, help_text='console配置')
    spec_use = models.SmallIntegerField(default=0,
                                        help_text="是否被job或集群指定使用, "
                                                  "1被集群使用，2被job使用")
    occupied_job_id = models.IntegerField(null=True, blank=True, help_text='被哪个任务所占用')
    broken_job_id = models.IntegerField(null=True, blank=True, help_text='关联机器故障job')
    broken_at = models.DateTimeField(null=True, help_text='故障时间')
    broken_reason = models.TextField(null=True, help_text='故障原因')

    class Meta:
        db_table = 'test_server'


class CloudServer(BaseModel):
    job_id = models.IntegerField(help_text='关联Job')
    provider = models.CharField(max_length=64, choices=TestServerEnums.CLOUD_SERVER_PROVIDER_CHOICES,
                                help_text='Provider')
    region = models.CharField(max_length=64, help_text='Region')
    zone = models.CharField(max_length=64, help_text='Zone')
    manufacturer = models.CharField(max_length=64, help_text='云厂商')
    ak_id = models.IntegerField(default=1, help_text='AK id')

    image = models.CharField(max_length=64, help_text='镜像')
    image_name = models.CharField(null=True, blank=True, max_length=64, help_text='镜像名称')
    bandwidth = models.IntegerField(help_text='最大带宽')
    storage_type = models.CharField(max_length=64, help_text='存储类型')
    storage_size = models.CharField(max_length=64, help_text='存储大小')
    storage_number = models.CharField(max_length=64, help_text='存储数量')
    system_disk_category = models.CharField(max_length=64, help_text='系统盘类型', default='cloud_ssd')
    system_disk_size = models.CharField(max_length=64, help_text='系统盘大小', default=50)
    extra_param = json.JSONField(default=dict(), help_text='扩展信息')
    sn = models.CharField(max_length=64, null=True, help_text='SN')
    tsn = models.CharField(max_length=64, null=True, help_text='TSN')
    release_rule = models.BooleanField(default=1, help_text='用完释放')
    # 模板
    template_name = models.CharField(max_length=64, help_text='模板名称')

    # 实例
    instance_id = models.CharField(max_length=64, help_text='Instance id')
    instance_name = models.CharField(max_length=64, help_text='Instance Name')

    instance_type = models.CharField(max_length=64, help_text='规格')
    # 1、instance:用户指定，2、模板：3、由模板产生的实例，根据以下两个字段区分
    is_instance = models.BooleanField(default=True, help_text='是否实例')
    parent_server_id = models.IntegerField(help_text='父级id')
    owner = models.IntegerField(null=True, help_text='Owner')
    description = models.CharField(max_length=1024, null=True, blank=True, help_text='描述')
    # 待定字段
    private_ip = models.CharField(max_length=64, help_text='私有IP')
    pub_ip = models.CharField(max_length=64, help_text='公有IP')
    hostname = models.CharField(max_length=64, help_text='Host Name')
    port = models.IntegerField(null=True, help_text='端口号')
    kernel_version = models.CharField(max_length=64, help_text='内核版本')
    state = models.CharField(max_length=64, choices=TestServerEnums.SERVER_STATE_CHOICES,
                             default='Available', help_text='状态')
    real_state = models.CharField(max_length=64, choices=TestServerEnums.SERVER_STATE_CHOICES, default='Available',
                                  help_text='真实状态')
    history_state = models.CharField(max_length=64, choices=TestServerEnums.SERVER_STATE_CHOICES, default='Available',
                                     help_text='历史状态')
    check_state_time = models.DateTimeField(null=True, help_text='最近一次检测机器真实状态的时间')
    channel_type = models.CharField(max_length=64, choices=TestServerEnums.SERVER_CHANNEL_TYPE_CHOICES,
                                    default='toneagent', help_text='通道类型')
    ws_id = models.CharField(max_length=8, db_index=True, help_text='关联Workspace')

    console_type = models.CharField(max_length=64, help_text='console类型')
    console_conf = models.CharField(max_length=64, help_text='console配置')
    spec_use = models.SmallIntegerField(default=0,
                                        help_text="是否被job或集群指定使用, "
                                                  "1被集群使用，2被job使用")
    occupied_job_id = models.IntegerField(null=True, blank=True, help_text='被哪个任务所占用')
    in_pool = models.BooleanField(default=True, help_text='是否在单机池中')
    broken_job_id = models.IntegerField(null=True, blank=True, help_text='关联机器故障job')
    broken_at = models.DateTimeField(null=True, help_text='故障时间')
    broken_reason = models.TextField(null=True, help_text='故障原因')

    class Meta:
        db_table = 'cloud_server'


class TestCluster(BaseModel):
    name = models.CharField(max_length=64, help_text='名称')
    cluster_type = models.CharField(max_length=64, choices=TestServerEnums.RUN_ENV_CHOICES, help_text='集群类型')
    is_occpuied = models.BooleanField(help_text='是否被占用', default=False)
    ws_id = models.CharField(max_length=64, help_text='ws_id')
    owner = models.IntegerField(null=True, help_text='Owner')
    description = models.CharField(max_length=1024, null=True, blank=True, help_text='描述')
    occupied_job_id = models.IntegerField(null=True, blank=True, help_text='被哪个任务所占用')

    class Meta:
        db_table = 'test_cluster'


class TestClusterServer(BaseModel):
    cluster_id = models.IntegerField(help_text='集群id')
    server_id = models.IntegerField(help_text='关联单机id')
    cluster_type = models.CharField(max_length=64, choices=TestServerEnums.RUN_ENV_CHOICES, help_text='集群类型')
    role = models.CharField(max_length=64, choices=TestServerEnums.CLUSTER_ROLE_CHOICES, help_text='集群角色')
    baseline_server = models.BooleanField(help_text='是否是基线机器')
    kernel_install = models.BooleanField(help_text='是否安装内核')
    var_name = models.CharField(max_length=64, help_text='变量名')

    class Meta:
        db_table = 'test_cluster_server'


class TestServerSnapshot(BaseModel):
    name = models.CharField(max_length=255, help_text='机器名称')
    ip = models.CharField(max_length=64, help_text='IP')
    sn = models.CharField(max_length=64, help_text='SN', null=True, blank=True)
    tsn = models.CharField(max_length=64, help_text='TSN', null=True, blank=True)
    hostname = models.CharField(max_length=64, help_text='Host Name', null=True, blank=True)
    # 逻辑
    app_group = models.CharField(max_length=64, help_text='APP GROUP', null=True, blank=True)
    app_state = models.CharField(max_length=64, help_text='应用状态', null=True, blank=True)
    security_domain = models.CharField(max_length=64, help_text='安全域', null=True, blank=True)
    idc = models.CharField(max_length=64, help_text='IDC', null=True, blank=True)
    parent_server_id = models.IntegerField(null=True, blank=True, help_text='父机器')
    # 硬件型号
    manufacturer = models.CharField(max_length=64, help_text='供应商', null=True, blank=True)
    device_type = models.CharField(max_length=64, choices=TestServerEnums.DEVICE_TYPE_CHOICES, help_text='机器类型',
                                   null=True, blank=True)
    device_mode = models.CharField(max_length=64, help_text='型号', null=True, blank=True)
    sm_name = models.CharField(max_length=64, help_text='机型', null=True, blank=True)
    # 硬件配置
    arch = models.CharField(max_length=64, help_text='ARCH', null=True, blank=True)
    cpu = models.CharField(max_length=64, help_text='CPU', null=True, blank=True)
    memory = models.CharField(max_length=64, help_text='内存', null=True, blank=True)
    storage = models.CharField(max_length=64, help_text='存储磁盘', null=True, blank=True)
    cpu_device = models.CharField(max_length=64, help_text='CPU类型', null=True, blank=True)
    memory_device = models.CharField(max_length=64, help_text='内存类型', null=True, blank=True)
    network = models.CharField(max_length=64, help_text='网络', null=True, blank=True)
    net_device = models.CharField(max_length=64, help_text='网络类型', null=True, blank=True)
    # 软件
    kernel = models.CharField(max_length=64, help_text='内核', null=True, blank=True)
    platform = models.CharField(max_length=64, help_text='平台', null=True, blank=True)
    uname = models.CharField(max_length=64, help_text='UName', null=True, blank=True)
    #
    state = models.CharField(max_length=64, choices=TestServerEnums.SERVER_STATE_CHOICES, default='Available',
                             help_text='状态')
    real_state = models.CharField(max_length=64, choices=TestServerEnums.SERVER_STATE_CHOICES, default='Available',
                                  help_text='真实状态')
    history_state = models.CharField(max_length=64, choices=TestServerEnums.SERVER_STATE_CHOICES, default='Available',
                                     help_text='历史状态')
    # state=1 use_type:平台或者用户手动reserve
    use_type = models.CharField(max_length=64, choices=TestServerEnums.USE_TYPE_CHOICES, help_text='Reserve类型',
                                null=True, blank=True)
    check_state_time = models.DateTimeField(null=True, help_text='最近一次检测机器真实状态的时间')
    description = models.CharField(max_length=64, help_text='描述', null=True, blank=True)

    channel_type = models.CharField(max_length=64, choices=TestServerEnums.SERVER_CHANNEL_TYPE_CHOICES,
                                    help_text='通道类型')
    channel_state = models.BooleanField(default=False, help_text='控制通道状态，是否部署完成')
    private_ip = models.CharField(max_length=64, help_text='私有IP', null=True, blank=True)
    owner = models.IntegerField(null=True, help_text='Owner')
    ws_id = models.CharField(max_length=8, db_index=True, help_text='关联Workspace')
    # 机器管理只展示单机池中的机器
    in_pool = models.BooleanField(default=True, help_text='是否在单机池中')

    console_type = models.CharField(max_length=64, help_text='console类型', null=True, blank=True)
    console_conf = models.CharField(max_length=64, help_text='console配置', null=True, blank=True)
    spec_use = models.SmallIntegerField(default=0,
                                        help_text="是否被job或集群指定使用, "
                                                  "1被集群使用，2被job使用")
    occupied_job_id = models.IntegerField(null=True, blank=True, help_text='被哪个任务所占用')
    source_server_id = models.IntegerField(db_index=True, null=True, help_text='来源机器id')
    job_id = models.IntegerField(null=True, blank=True, default=0, db_index=True)
    distro = models.CharField(max_length=256, null=True, help_text='发行版本')
    gcc = models.TextField(null=True, help_text='gcc版本')
    rpm_list = models.TextField(null=True, help_text='rpm包')
    glibc = models.TextField(null=True, help_text='glibc信息')
    memory_info = models.TextField(null=True, help_text='内存信息')
    disk = models.TextField(null=True, help_text='磁盘信息')
    cpu_info = models.TextField(null=True, help_text='CPU信息')
    ether = models.TextField(null=True, help_text='网卡信息')
    broken_job_id = models.IntegerField(null=True, blank=True, help_text='关联机器故障job')
    broken_at = models.DateTimeField(null=True, help_text='故障时间')
    kernel_version = models.CharField(max_length=64, help_text='内核版本', null=True, blank=True)
    product_version = models.CharField(help_text='product_version', null=True, blank=True, max_length=64)
    broken_reason = models.TextField(null=True, help_text='故障原因')

    class Meta:
        db_table = 'test_server_snapshot'


class CloudServerSnapshot(BaseModel):
    job_id = models.IntegerField(help_text='关联Job', null=True, blank=True, default=0, db_index=True)
    provider = models.CharField(max_length=64, choices=TestServerEnums.CLOUD_SERVER_PROVIDER_CHOICES,
                                help_text='Provider', null=True, blank=True)
    region = models.CharField(max_length=64, help_text='Region', null=True, blank=True)
    zone = models.CharField(max_length=64, help_text='Zone', null=True, blank=True)
    manufacturer = models.CharField(max_length=64, help_text='云厂商', null=True, blank=True)
    ak_id = models.IntegerField(default=1, help_text='AK id', null=True, blank=True)

    image = models.CharField(max_length=64, help_text='镜像', null=True, blank=True)
    image_name = models.CharField(null=True, blank=True, max_length=64, help_text='镜像名称')
    bandwidth = models.IntegerField(help_text='最大带宽', null=True, blank=True)
    storage_type = models.CharField(max_length=64, help_text='存储类型', null=True, blank=True)
    storage_size = models.CharField(max_length=64, help_text='存储大小', null=True, blank=True)
    storage_number = models.CharField(max_length=64, help_text='存储数量', null=True, blank=True)
    system_disk_category = models.CharField(max_length=64, help_text='系统盘类型', default='cloud_ssd')
    system_disk_size = models.CharField(max_length=64, help_text='系统盘大小', default=50)
    extra_param = json.JSONField(default=dict(), help_text='扩展信息')
    sn = models.CharField(max_length=64, null=True, help_text='SN', blank=True)
    tsn = models.CharField(max_length=64, null=True, help_text='TSN')
    release_rule = models.BooleanField(default=1, help_text='用完释放', null=True, blank=True)
    # 模板
    template_name = models.CharField(max_length=64, help_text='模板名称', null=True, blank=True)

    # 实例
    instance_id = models.CharField(max_length=64, help_text='Instance id', null=True, blank=True)
    instance_name = models.CharField(max_length=64, help_text='Instance Name', null=True, blank=True)

    instance_type = models.CharField(max_length=64, help_text='规格', null=True, blank=True)
    # 1、instance:用户指定，2、模板：3、由模板产生的实例，根据以下两个字段区分
    is_instance = models.BooleanField(default=True, help_text='是否实例')
    parent_server_id = models.IntegerField(help_text='父级id', null=True, blank=True)
    owner = models.IntegerField(null=True, help_text='Owner')
    description = models.CharField(max_length=1024, null=True, blank=True, help_text='描述')
    # 待定字段
    private_ip = models.CharField(max_length=64, help_text='私有IP', null=True, blank=True)
    pub_ip = models.CharField(max_length=64, help_text='公有IP', null=True, blank=True)
    hostname = models.CharField(max_length=64, help_text='Host Name', null=True, blank=True)
    port = models.IntegerField(null=True, help_text='端口号')
    kernel_version = models.CharField(max_length=64, help_text='内核版本', null=True, blank=True)
    state = models.CharField(max_length=64, choices=TestServerEnums.SERVER_STATE_CHOICES,
                             default='Available', help_text='状态')
    real_state = models.CharField(max_length=64, choices=TestServerEnums.SERVER_STATE_CHOICES, default='Available',
                                  help_text='真实状态')
    history_state = models.CharField(max_length=64, choices=TestServerEnums.SERVER_STATE_CHOICES, default='Available',
                                     help_text='历史状态')
    check_state_time = models.DateTimeField(null=True, help_text='最近一次检测机器真实状态的时间')
    channel_type = models.CharField(max_length=64, choices=TestServerEnums.SERVER_CHANNEL_TYPE_CHOICES,
                                    help_text='通道类型', default='toneagent')
    ws_id = models.CharField(max_length=8, db_index=True, help_text='关联Workspace')

    console_type = models.CharField(max_length=64, help_text='console类型', null=True, blank=True)
    console_conf = models.CharField(max_length=64, help_text='console配置', null=True, blank=True)
    spec_use = models.SmallIntegerField(default=0,
                                        help_text="是否被job或集群指定使用, "
                                                  "1被集群使用，2被job使用")
    occupied_job_id = models.IntegerField(null=True, blank=True, help_text='被哪个任务所占用')
    in_pool = models.BooleanField(default=True, help_text='是否在单机池中')
    source_server_id = models.IntegerField(db_index=True, null=True, help_text='来源机器id')
    arch = models.CharField(max_length=64, help_text='ARCH', null=True, blank=True)
    distro = models.CharField(max_length=256, null=True, help_text='发行版本')
    gcc = models.TextField(null=True, help_text='gcc版本')
    rpm_list = models.TextField(null=True, help_text='rpm包')
    glibc = models.TextField(null=True, help_text='glibc信息')
    memory_info = models.TextField(null=True, help_text='内存信息')
    disk = models.TextField(null=True, help_text='磁盘信息')
    cpu_info = models.TextField(null=True, help_text='CPU信息')
    ether = models.TextField(null=True, help_text='网卡信息')
    broken_job_id = models.IntegerField(null=True, blank=True, help_text='关联机器故障job')
    broken_at = models.DateTimeField(null=True, help_text='故障时间')
    product_version = models.CharField(help_text='product_version', null=True, blank=True, max_length=64)
    broken_reason = models.TextField(null=True, help_text='故障原因')

    class Meta:
        db_table = 'cloud_server_snapshot'


class TestClusterSnapshot(BaseModel):
    name = models.CharField(max_length=64, help_text='名称')
    cluster_type = models.CharField(max_length=64,
                                    choices=TestServerEnums.RUN_ENV_CHOICES,
                                    help_text='集群类型')
    is_occpuied = models.BooleanField(help_text='是否被占用', default=False)
    ws_id = models.CharField(max_length=64, help_text='ws_id')
    owner = models.IntegerField(null=True, help_text='Owner')
    description = models.CharField(max_length=1024, null=True, blank=True, help_text='描述')
    source_cluster_id = models.IntegerField(db_index=True, help_text='来源集群id')
    job_id = models.IntegerField(null=True)

    class Meta:
        db_table = 'test_cluster_snapshot'


class TestClusterServerSnapshot(BaseModel):
    cluster_id = models.IntegerField(help_text='集群id')
    server_id = models.IntegerField(help_text='关联单机id')
    cluster_type = models.CharField(max_length=64, choices=TestServerEnums.RUN_ENV_CHOICES, help_text='集群类型')
    role = models.CharField(max_length=64, choices=TestServerEnums.CLUSTER_ROLE_CHOICES, help_text='集群角色')
    baseline_server = models.BooleanField(help_text='是否是基线机器', default=False)
    kernel_install = models.BooleanField(help_text='是否安装内核', default=False)
    var_name = models.CharField(max_length=64, help_text='变量名', null=True, blank=True)
    source_cluster_server_id = models.IntegerField(db_index=True, help_text='来源集群机器id')
    job_id = models.IntegerField(null=True)

    class Meta:
        db_table = 'test_cluster_server_snapshot'


class ServerTag(BaseModel):
    name = models.CharField(max_length=255, help_text='标签名称')
    tag_color = models.CharField(max_length=64, help_text='标签颜色', null=True)
    create_user = models.IntegerField(help_text='创建人', null=True)
    update_user = models.IntegerField(help_text='修改人', null=True)
    description = models.CharField(max_length=1024, null=True, blank=True, help_text='描述')
    ws_id = models.CharField(max_length=64, help_text='workspace id')

    class Meta:
        db_table = 'server_tag'


class ServerTagRelation(BaseModel):
    run_environment = models.CharField(max_length=64,
                                       choices=TestServerEnums.RUN_ENV_CHOICES,
                                       default='cluster',
                                       help_text='运行环境')
    object_type = models.CharField(max_length=64,
                                   choices=TestServerEnums.OBJECT_TYPE_CHOICES,
                                   help_text='关联对象类型')
    object_id = models.IntegerField(db_index=True, help_text='关联对象ID')
    server_tag_id = models.IntegerField(db_index=True, help_text='关联server_tagID')

    class Meta:
        db_table = 'server_tag_relation'


class CloudAk(BaseModel):
    name = models.CharField(max_length=64, help_text='ak name')
    provider = models.CharField(max_length=64,
                                choices=TestServerEnums.CLOUD_SERVER_PROVIDER_CHOICES,
                                help_text='')
    access_id = models.CharField(max_length=128, help_text='')
    access_key = models.CharField(max_length=1024, help_text='')
    resource_group_id = models.CharField(max_length=32, null=True, blank=True, help_text='资源组ID')
    vm_quota = models.CharField(max_length=8, help_text='创建VM限额', default='*')
    description = models.CharField(max_length=1024, null=True, blank=True, help_text='描述')
    ws_id = models.CharField(max_length=8, db_index=True, help_text='关联Workspace')
    enable = models.BooleanField(default=True, help_text='启用状态')
    creator = models.IntegerField(help_text='创建者', null=True)
    update_user = models.IntegerField(help_text='修改者', null=True)

    class Meta:
        db_table = 'cloud_ak'


class CloudImage(BaseModel):
    ak_id = models.IntegerField(db_index=True, help_text='ak id')
    provider = models.CharField(max_length=32, help_text='provider name')
    region = models.CharField(max_length=64, help_text='region/location id')

    public_type = models.SmallIntegerField(default=1, null=True,
                                           help_text='公开类型，公共镜像0，自定义镜像1')
    usage_type = models.CharField(max_length=32, null=True, default='instance',
                                  help_text='instance or container')
    login_user = models.CharField(max_length=32, null=True, default='root', help_text='登陆用户名')

    image_id = models.CharField(max_length=128, db_index=True, help_text='image_id')
    image_name = models.CharField(max_length=100, blank=True, default='')
    image_version = models.CharField(max_length=64, help_text='image版本信息')
    image_size = models.CharField(max_length=32, null=True, blank=True, help_text='image size')
    os_name = models.CharField(max_length=64, null=True, default='CenOS 7.4 bit', help_text='操作系统名称版本')
    os_type = models.CharField(max_length=16, null=True, default='linux', help_text='OS type linux, windows')
    os_arch = models.CharField(max_length=16, blank=True, default='x86_64', help_text='os arch, x86_64, arm')
    platform = models.CharField(max_length=32, null=True, default='CentOS', help_text='发行商 CentOS, Ubuntu等')
    ws_id = models.CharField(max_length=8, db_index=True, help_text='关联Workspace')
    creator = models.IntegerField(help_text='创建者', null=True)
    update_user = models.IntegerField(help_text='修改者', null=True)

    class Meta:
        db_table = 'cloud_image'


class ServerRecoverRecord(BaseModel):
    sn = models.CharField(max_length=64, help_text='SN', null=True, blank=True)
    ip = models.CharField(max_length=64, help_text='IP')
    reason = models.TextField(null=True, blank=True, help_text='故障恢复原因')
    broken_at = models.DateTimeField(null=True, help_text='故障时间')
    recover_at = models.DateTimeField(null=True, help_text='恢复时间')
    broken_job_id = models.IntegerField(null=True, blank=True, help_text='关联机器故障job')

    class Meta:
        db_table = 'server_recover_record'
