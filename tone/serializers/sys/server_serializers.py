from rest_framework import serializers

from tone.core.common.constant import SERVER_REAL_STATE_RETURN_MAP
from tone.core.common.serializers import CommonSerializer
from tone.models import TestServer, CloudServer, TestCluster, TestClusterServer, \
    ServerTag, ServerTagRelation, CloudAk, User, CloudImage


class TestServerSerializer(CommonSerializer):
    owner_name = serializers.SerializerMethodField()
    channel_type = serializers.CharField(source='get_channel_type_display')
    device_type = serializers.CharField(source='get_device_type_display')
    use_type = serializers.CharField(source='get_use_type_display')
    tag_list = serializers.SerializerMethodField()
    sub_server_list = serializers.SerializerMethodField()
    emp_id = serializers.SerializerMethodField()
    real_state = serializers.SerializerMethodField()

    class Meta:
        model = TestServer
        exclude = ['is_deleted']

    @staticmethod
    def get_real_state(obj):
        return SERVER_REAL_STATE_RETURN_MAP.get(obj.real_state)

    @staticmethod
    def get_emp_id(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.emp_id

    @staticmethod
    def get_tag_list(obj):
        tag_id_list = ServerTagRelation.objects.filter(run_environment='aligroup', object_type='standalone',
                                                       object_id=obj.id). \
            values_list('server_tag_id', flat=True)
        return ServerTagSerializer(ServerTag.objects.filter(id__in=tag_id_list), many=True).data

    @staticmethod
    def get_sub_server_list(obj):
        return TestSubServerSerializer(TestServer.objects.filter(ws_id=obj.ws_id,
                                                                 parent_server_id=obj.id), many=True).data

    @staticmethod
    def get_owner_name(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.last_name or owner.first_name


class SpecifyTestServerSerializer(CommonSerializer):
    owner_name = serializers.SerializerMethodField()
    emp_id = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()

    class Meta:
        model = TestServer
        fields = ['id', 'ip', 'state', 'owner', 'owner_name', 'emp_id', 'first_name', 'last_name', 'sn']

    @staticmethod
    def get_owner_name(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.last_name or owner.first_name

    @staticmethod
    def get_first_name(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.first_name

    @staticmethod
    def get_last_name(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.last_name

    @staticmethod
    def get_emp_id(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.emp_id


class TestSubServerSerializer(CommonSerializer):
    owner_name = serializers.SerializerMethodField()
    channel_type = serializers.CharField(source='get_channel_type_display')
    device_type = serializers.CharField(source='get_device_type_display')
    use_type = serializers.CharField(source='get_use_type_display')
    tag_list = serializers.SerializerMethodField()
    emp_id = serializers.SerializerMethodField()
    real_state = serializers.SerializerMethodField()

    class Meta:
        model = TestServer
        exclude = ['is_deleted']

    @staticmethod
    def get_real_state(obj):
        return SERVER_REAL_STATE_RETURN_MAP.get(obj.real_state)

    @staticmethod
    def get_emp_id(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.emp_id

    @staticmethod
    def get_tag_list(obj):
        tag_id_list = ServerTagRelation.objects.filter(run_environment='aligroup', object_type='standalone',
                                                       object_id=obj.id). \
            values_list('server_tag_id', flat=True)
        return ServerTagSerializer(ServerTag.objects.filter(id__in=tag_id_list), many=True).data

    @staticmethod
    def get_owner_name(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.last_name or owner.first_name


class TestServerAppGroupSerializer(CommonSerializer):
    class Meta:
        model = TestServer
        fields = ['app_group']


class CloudServerSerializer(CommonSerializer):
    owner_name = serializers.SerializerMethodField()
    tag_list = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    emp_id = serializers.SerializerMethodField()
    manufacturer_ak = serializers.SerializerMethodField()
    region_zone = serializers.SerializerMethodField()
    ak_name = serializers.SerializerMethodField()
    bandwidth = serializers.SerializerMethodField()
    image_name = serializers.SerializerMethodField()
    pub_ip = serializers.SerializerMethodField()
    extra_param = serializers.JSONField()
    real_state = serializers.SerializerMethodField()

    class Meta:
        model = CloudServer
        exclude = ['is_deleted']

    @staticmethod
    def get_real_state(obj):
        return SERVER_REAL_STATE_RETURN_MAP.get(obj.real_state)

    @staticmethod
    def get_pub_ip(obj):
        # 公网ip暂不对外开放
        # return '******'
        return obj.private_ip

    @staticmethod
    def get_image_name(obj):
        return obj.image_name if obj.image_name else obj.image

    @staticmethod
    def get_bandwidth(obj):
        bandwidth = 10   # 云上机器镜像最小为10
        if str(obj.bandwidth).isdigit():
            if int(obj.bandwidth) > 10:
                bandwidth = obj.bandwidth
        return bandwidth

    @staticmethod
    def get_ak_name(obj):
        if obj.ak_id and CloudAk.objects.filter(id=obj.ak_id, query_scope='all').exists():
            return CloudAk.objects.filter(id=obj.ak_id, query_scope='all').first().name

    @staticmethod
    def get_manufacturer_ak(obj):
        if obj.ak_id:
            ak = CloudAk.objects.filter(id=obj.ak_id, query_scope='all').first()
            if ak:
                return '{}/{}'.format(obj.manufacturer, ak.name)

    @staticmethod
    def get_region_zone(obj):
        return '{}/{}'.format(obj.region, obj.zone)

    @staticmethod
    def get_emp_id(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.emp_id

    @staticmethod
    def get_tag_list(obj):
        tag_id_list = ServerTagRelation.objects.filter(run_environment='aliyun', object_type='standalone',
                                                       object_id=obj.id). \
            values_list('server_tag_id', flat=True)
        return ServerTagSerializer(ServerTag.objects.filter(id__in=tag_id_list), many=True).data

    @staticmethod
    def get_owner_name(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.last_name or owner.first_name

    @staticmethod
    def get_name(obj):
        if obj.is_instance:
            return obj.instance_name
        else:
            return obj.template_name


class TestClusterSerializer(CommonSerializer):
    owner_name = serializers.SerializerMethodField()
    tag_list = serializers.SerializerMethodField()
    emp_id = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()

    class Meta:
        model = TestCluster
        exclude = ['is_deleted']

    @staticmethod
    def get_emp_id(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.emp_id

    @staticmethod
    def get_tag_list(obj):
        tag_id_list = ServerTagRelation.objects.filter(object_type='cluster', object_id=obj.id). \
            values_list('server_tag_id', flat=True)
        return ServerTagSerializer(ServerTag.objects.filter(id__in=tag_id_list), many=True).data

    @staticmethod
    def get_owner_name(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.last_name or owner.first_name

    @staticmethod
    def get_state(obj):
        test_cluster_server_list = TestClusterServer.objects.filter(cluster_id=obj.id)
        if test_cluster_server_list:
            test_server_state_list = []
            for test_cluster_server in list(test_cluster_server_list):
                server_id = test_cluster_server.server_id
                test_server = TestServer.objects.filter(id=server_id).first()
                if test_server:
                    test_server_state = test_server.state
                    test_server_state_list.append(test_server_state)
            if 'Unusable' in test_server_state_list:
                return 'Unusable'
            else:
                return 'Available'


class TestClusterServerSerializer(CommonSerializer):
    test_server = serializers.SerializerMethodField()

    class Meta:
        model = TestClusterServer
        exclude = ['is_deleted']

    @staticmethod
    def get_test_server(obj):
        if obj.cluster_type == 'aligroup':
            return TestServerSerializer(TestServer.objects.filter(id=obj.server_id).first(), many=False).data
        else:
            return CloudServerSerializer(CloudServer.objects.filter(id=obj.server_id).first(), many=False).data


class ServerTagSerializer(CommonSerializer):
    create_user = serializers.SerializerMethodField()
    update_user = serializers.SerializerMethodField()

    class Meta:
        model = ServerTag
        exclude = ['is_deleted']

    @staticmethod
    def get_create_user(obj):
        owner = User.objects.filter(id=obj.create_user).first()
        if owner is None:
            return '系统预设'
        return owner.last_name or owner.first_name

    @staticmethod
    def get_update_user(obj):
        owner = User.objects.filter(id=obj.update_user).first()
        if owner is None:
            return '系统预设'
        return owner.last_name or owner.first_name


class ServerTagRelationSerializer(CommonSerializer):
    class Meta:
        model = ServerTagRelation
        exclude = ['is_deleted']


class CloudAkSerializer(CommonSerializer):
    creator = serializers.SerializerMethodField()
    update_user = serializers.SerializerMethodField()
    access_id = serializers.SerializerMethodField()
    access_key = serializers.SerializerMethodField()

    class Meta:
        model = CloudAk
        exclude = ['is_deleted']

    @staticmethod
    def get_access_id(obj):
        return '{}******{}'.format(obj.access_id[:4], obj.access_id[-4:])

    @staticmethod
    def get_access_key(obj):
        return '{}******{}'.format(obj.access_key[:4], obj.access_key[-4:])

    @staticmethod
    def get_creator(obj):
        creator_name = None
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    @staticmethod
    def get_update_user(obj):
        update_user = None
        creator = User.objects.filter(id=obj.update_user).first()
        if creator:
            update_user = creator.first_name if creator.first_name else creator.last_name
        return update_user


class CloudImageSerializer(CommonSerializer):
    creator = serializers.SerializerMethodField()
    update_user = serializers.SerializerMethodField()
    ak_name = serializers.SerializerMethodField()

    class Meta:
        model = CloudImage
        exclude = ['is_deleted', 'public_type', 'usage_type', 'login_user', 'image_size',
                   'os_name', 'os_type', 'os_arch']

    @staticmethod
    def get_creator(obj):
        creator_name = None
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    @staticmethod
    def get_update_user(obj):
        update_user = None
        creator = User.objects.filter(id=obj.update_user).first()
        if creator:
            update_user = creator.first_name if creator.first_name else creator.last_name
        return update_user

    @staticmethod
    def get_ak_name(obj):
        ak_name = ''
        ak_obj = CloudAk.objects.filter(id=obj.ak_id, query_scope='all').first()
        if ak_obj:
            ak_name = ak_obj.name
        return ak_name
