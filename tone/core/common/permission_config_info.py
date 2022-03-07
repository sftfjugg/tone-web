"""
路由权限配置
角色信息：
+----------------+-------------------+
| title          | description       |
+----------------+-------------------+
| sys_admin      | 系统管理员        |
| user           | 普通用户          ||
| ws_tester_admin       | 管理员            |
| ws_tester  | 测试管理员（WS）  |
| ws_member      | workspace成员     |
+----------------+-------------------+
"""

SYS_ROLE_MAP = {
    'sys_admin': ['sys_admin', 'user'],
    'user': ['user']
}
WS_ROLE_MAP = {
    # 'ws_owner': ['ws_tester_admin', 'ws_tester', 'ws_member', 'ws_tourist'],
    'ws_tester_admin': ['ws_tester', 'ws_member', 'ws_tourist'],
    'ws_tester': ['ws_tester', 'ws_member', 'ws_tourist'],
    'ws_member': ['ws_member'],
    'ws_tourist': ['ws_tourist'],
}
# 白名单
VALID_URL_LIST = [
    "^/$", "/api/job/create/",
    "/favicon.ico", "/admin/.*", "/api/job/query/"
]
SYS_PERMISSION_CONFIG = {
    # 用户管理
    '/api/auth/user/': {
        'POST': {'sys_admin'},
    },
    # sys申请审批
    '/api/sys/approve/': {
        'GET': {'sys_admin', 'ws_permission'},
        'POST': {'sys_admin', 'ws_permission'},
    },
    '/api/sys/approve/quantity/': {
        'GET': {'sys_admin', 'ws_permission'},
    },
    # Workspace管理
    '/api/sys/workspace/': {
        'POST': {'super_admin', 'sys_admin'},
        'DELETE': {'super_admin', 'sys_admin', 'ws_permission'},
        'PUT': {'super_admin', 'sys_admin', 'ws_permission'},
    },
    # Test Suite 管理
    '/api/case/test_suite/': {
        'POST': {'sys_admin'},
        'DELETE': {'sys_admin'},
        'PUT': {'sys_admin'},
    },
    # Domain配置
    '/api/case/test_domain/': {
        'POST': {'sys_admin'},
        'DELETE': {'sys_admin'},
        'PUT': {'sys_admin'},
    },
    # 内核管理
    '/api/sys/kernel/': {
        'POST': {'sys_admin'},
        'DELETE': {'sys_admin'},
        'PUT': {'sys_admin'},
    },
    # 基础配置管理
    '/api/sys/config/': {
        'GET': {'sys_admin'},
        'POST': {'sys_admin'},
        'DELETE': {'sys_admin'},
        'PUT': {'sys_admin'},
    },
    # 帮助文档
    '/api/sys/help_doc/': {
        'POST': {'sys_admin'},
        'DELETE': {'sys_admin'},
        'PUT': {'sys_admin'},
    },
    # TestFarm配置
    '/api/sys/test_farm/': {
        'POST': {'sys_admin'},
    },
}

WS_PERMISSION_CONFIG = {
    # ws申请审批
    '/api/sys/approve/': {
        # 'GET': {'ws_owner', 'ws_tester_admin'},A
        'POST': {'ws_owner', 'ws_tester_admin'},
    },
    # '/api/sys/approve/quantity/': {
    #     'GET': {'ws_owner', 'ws_tester_admin'},
    # },
    # workspace配置：基础配置、成员管理、审批管理
    '/api/sys/workspace/': {
        'PUT': {'ws_owner'},
        'DELETE': {'ws_owner'},
    },
    # WS成员： 增加、修改、删除
    '/api/sys/workspace/member/': {
        'GET': {'ws_owner', 'ws_tester_admin', 'ws_tester', 'ws_member'},
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'PUT': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'DELETE': {'ws_owner', 'ws_tester_admin'},
    },
    '/api/auth/role/': {
        'GET': {'ws_owner', 'ws_tester_admin', 'ws_tester', 'ws_member'},
    },

    # 创建job
    '/api/job/test/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'DELETE': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },

    # Job配置：Job类型管理、模板管理、Job标签管理
    '/api/job/type/': {
        'POST': {'ws_owner', 'ws_tester_admin'},
        'PUT': {'ws_owner', 'ws_tester_admin'},
        'DELETE': {'ws_owner', 'ws_tester_admin'},
    },
    '/api/job/template/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'PUT': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'DELETE': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    '/api/job/template/detail/': {
        'GET': {'ws_owner', 'ws_tester_admin', 'ws_tester', 'ws_member'},
    },
    '/api/job/tag/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'PUT': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    # 基线管理：内网基线、云上基线
    '/api/baseline/list/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'PUT': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'DELETE': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    # 功能基线详情
    '/api/baseline/funcs/detail/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester', 'ws_member'},
        'PUT': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'DELETE': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    # 性能基线详情
    '/api/baseline/perfs/detail/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester', 'ws_member'},
        'PUT': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'DELETE': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    # 机器管理：内网、云上、调度标签、云上测试配置
    # 内网单机
    '/api/server/test_server/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    # 内网集群 / 云上集群
    '/api/server/test_cluster/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    # 云上单机 机器单机/机器实例
    '/api/server/cloud_server/': {
        # 'GET': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    # 调度标签
    '/api/server/server_tag/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    # 云上测试配置 ak / image
    '/api/server/cloud_ak/': {
        'GET': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'PUT': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'DELETE': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    '/api/server/cloud_image/': {
        'GET': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'PUT': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'DELETE': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    # WS下的Test suite管理
    '/api/case/workspace/case/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    '/api/case/workspace/case/batch/add/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    # 产品管理
    '/api/sys/product/': {
        'POST': {'ws_owner', 'ws_tester_admin'},
        'PUT': {'ws_owner', 'ws_tester_admin'},
        'DELETE': {'ws_owner', 'ws_tester_admin'},
    },
    '/api/sys/project/': {
        'POST': {'ws_owner', 'ws_tester_admin'},
        'PUT': {'ws_owner', 'ws_tester_admin'},
        'DELETE': {'ws_owner', 'ws_tester_admin'},
    },
    '/api/sys/repository/': {
        'POST': {'ws_owner', 'ws_tester_admin'},
        'PUT': {'ws_owner', 'ws_tester_admin'},
        'DELETE': {'ws_owner', 'ws_tester_admin'},
    },
    # Branch
    '/api/sys/branch/': {
        'POST': {'ws_owner', 'ws_tester_admin'},
        'PUT': {'ws_owner', 'ws_tester_admin'},
        'DELETE': {'ws_owner', 'ws_tester_admin'},
    },

    # Job结果修改标签 /api/job/tag/relation/
    '/api/job/tag/relation/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester', 'ws_member'},
    },
    # Job结果修改备注
    '/api/job/test/editor/note/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester', 'ws_member'},
    },
    # 计划管理
    '/api/plan/list/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester', 'ws_member'},
    },
    '/api/plan/detail/': {
        'PUT': {'ws_owner', 'ws_tester_admin', 'ws_tester', 'ws_member'},
        'DELETE': {'ws_owner', 'ws_tester_admin', 'ws_tester', 'ws_member'},
    },
    # 计划结果
    '/api/plan/result/': {
        'DELETE': {'ws_owner', 'ws_tester_admin', 'ws_tester', 'ws_member'},
    },
    '/api/plan/result/detail/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester', 'ws_member'},
    },
    # 报告模板
    '/api/report/template/list/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester', 'ws_member'},
    },
    '/api/report/template/detail/': {
        'PUT': {'ws_owner', 'ws_tester_admin', 'ws_tester', 'ws_member'},
        'DELETE': {'ws_owner', 'ws_tester_admin', 'ws_tester', 'ws_member'},
    },
    '/api/report/template/copy/': {
        'POST': {'ws_owner', 'ws_tester_admin', 'ws_tester', 'ws_member'},
    },

    # 测试报告
    '/api/report/test/report/': {
        'POST': {'ws_owner', 'ws_admin', 'ws_tester_admin', 'ws_tester'},
        'PUT': {'ws_owner', 'ws_admin', 'ws_tester_admin', 'ws_tester'},
        'DELETE': {'ws_owner', 'ws_admin', 'ws_tester_admin', 'ws_tester'},
    },

    '/api/job/test/upload/offline/': {
        'POST': {'ws_owner', 'ws_admin', 'ws_tester_admin', 'ws_tester'},
    },
}

RE_PERMISSION_CONFIG = {
    # 机器管理——调度标签详情
    r'^/api/server/server_tag/detail/\d*/': {
        'PUT': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'DELETE': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    # 内网单机详情
    r'^/api/server/test_server/detail/\d*/': {
        'PUT': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'DELETE': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    # 云上单机详情
    r'^/api/server/cloud_server/detail/\d*/': {
        'PUT': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'DELETE': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    # 集群详情
    r'^/api/server/test_cluster/detail/\d*/': {
        'PUT': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'DELETE': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    # 内网集群机器详情
    r'^/api/server/test_cluster/test_server/detail/\d*/': {
        'PUT': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'DELETE': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
    # 云上集群机器详情
    r'^/api/server/test_cluster/cloud_server/detail/\d*/': {
        'PUT': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
        'DELETE': {'ws_owner', 'ws_tester_admin', 'ws_tester'},
    },
}
