class TestServerEnums:
    SERVER_STATE_CHOICES = (
        ('Available', 'Available'),
        ('Occupied', 'Occupied'),
        ('Broken', 'Broken'),
        ('Reserved', 'Reserved'),
        ('Unusable', 'Unusable')
    )

    RUN_ENV_CHOICES = (
        ('aligroup', '内网'),
        ('aliyun', '云上')
    )

    SERVER_CHANNEL_TYPE_CHOICES = (
        ('staragent', 'staragent'),
        ('toneagent', 'toneagent')
    )

    DEVICE_TYPE_CHOICES = (
        ('phy_server', '物理机'),
        ('vm', '虚拟机')
    )

    USE_TYPE_CHOICES = (
        ('task', '系统占用'),
        ('user', '用户手动占用')
    )

    CLOUD_SERVER_PROVIDER_CHOICES = (
        ('aliyun_ecs', '阿里云ECS'),
        ('aliyun_eci', '阿里云ECI')
    )

    CLUSTER_ROLE_CHOICES = (
        ('local', 'local'),
        ('remote', 'remote')
    )

    RUN_MODE_CHOICES = (
        ('standalone', '单机'),
        ('cluster', '集群')
    )

    OBJECT_TYPE_CHOICES = (
        ('cluster', 'cluster'),
        ('standalone', 'standalone')
    )
