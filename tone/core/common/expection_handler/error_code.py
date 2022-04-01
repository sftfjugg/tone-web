# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""


class ErrorCode(object):
    """
    common: 800~1000
    auth: 1001~1200
    sys: 1201~1300
    job: 1301~1400
    """
    SUCCESS = 'success'
    CODE = 200

    # common
    PROGRAM_ERROR = (500, "程序出错")

    NAME_NEED = (800, "缺少参数name")

    WS_NEED = (801, "缺少参数ws_id")

    JOB_NEED = (802, "缺少参数job_id")

    ID_NEED = (803, "缺少参数记录id")

    USERNAME_NOT_REGISTER = (804, "该用户名未注册或未配置token")

    TOKEN_FORMAT_ERROR = (997, "token格式错误")

    TOKEN_OVERDUE = (998, "token已过期")

    TOKEN_INVALID = (999, "token无效")

    TOKEN_NEED = (1000, "缺少参数token")

    # auth: 1001~1200
    TOKEN_ERROR = (1001, "token错误")

    PERMISSION_ERROR = (1002, "没有权限")

    LOGIN_ERROR = (1003, "请先登录")

    # sys: 1201~1300
    WS_NONEXISTENT = (1201, "workspace不存在")

    KERNEL_NONEXISTENT = (1202, "kernel_info不存在")

    KERNEL_NAME_LACK = (1203, "kernel name is must need !")

    KERNEL_VERSION_LACK = (1204, "kernel version is must need !")

    KERNEL_PACKAGE_LACK = (1205, "kernel_link, devel_link, headers_link is must need !")

    KERNEL_ID_LACK = (1206, "kernel_id is must need !")

    KERNEL_VERSION_DUPLICATION = (1207, "已存在同名version")

    TAG_NONEXISTENT = (1301, "该ws下tag不存在")

    TAG_DUPLICATION = (1302, "已存在同名tag")

    TYPE_NONEXISTENT = (1303, "job_type不存在")

    TYPE_DUPLICATION = (1304, "已存在同名job_type")

    TYPE_ID_LACK = (1305, "job_type id must need")

    ITEM_NONEXISTENT = (1306, "的原子项不存在")

    SYS_TYPE_ATOMIC = (1307, "系统类型无法删除")

    ITEM_MUST_DIC = (1308, "item_dic is must dict !")

    SERVER_TYPE_LACK = (1309, "server_type is must need !")

    TEST_TYPE_LACK = (1310, "test_type is must need !")

    TAG_ID_NEED = (1311, "tag_id is must need !")

    TEST_JOB_NONEXISTENT = (1351, "Job不存在")

    TEST_CONF_NEED = (1352, "test_config is must need !")

    TEST_CONF_LIST = (1353, "test_config must be list !")

    TEST_SUITE_NEED = (1354, "test_suite_id must need")

    TEST_SUITE_NAME_NEED = (1354, "test_suite_name must need")

    CASES_LIST = (1354, "cases_list must be list !")

    SERVER_NONEXISTENT = (1355, "workspace下机器不存在")

    SERVER_STATUS = (1356, "指定机器Broken，请检查指定机器是否可用")

    CLUSTER_NO_SERVER = (1357, "集群无关联机器")

    SERVER_TYPE_MUTEX = (1358, "case server_object_id customer_server server_tag_id mutex!")

    DATA_FORM_ERROR = (1359, "data_from 参数有误 !")

    CONFIG_ID_NEED = (1360, "config is must need !")

    CONFIG_NONEXISTENT = (1361, "config不存在")

    CONFIG_DUPLICATION = (1362, "已存在同名config")

    CONFIG_KEY_NEED = (1363, "config_key 必须传")

    CONFIG_TYPE_NEED = (1364, "config_type 必须传")

    TEST_TEMPLATE_NONEXISTENT = (1365, "TestTemplate不存在")

    TEMPLATE_NEED = (1366, "template_id 必须传")

    DEFAULT_DUPLICATION = (1367, "同一workspace下默认job_type唯一")

    PRODUCT_DUPLICATION = (1368, "workspace下已存在同名product")

    PRODUCT_ID_NEED = (1369, "prd_id is must need !")

    PRODUCT_NEED = (1370, "product_id 必须传")

    PROJECT_DUPLICATION = (1371, "已存在同名project")

    PRODUCT_VERSION_DUPLICATION = (1390, "已存在同名产品版本")

    PRODUCT_VERSION_NEED = (1391, "产品版本必传")

    PROJECT_ID_NEED = (1372, "project_id is must need !")

    GIT_URL_NEED = (1373, "git_url 必须传")

    REPOSITORY_DUPLICATION = (1374, "project下已存在同名仓库")

    REPOSITORY_ID_NEED = (1375, "repository_id is must need !")
    BRANCH_DUPLICATION = (1376, "仓库下已存在同名branch")

    BRANCH_ID_NEED = (1377, "branch_id is must need !")

    SUITE_NEED = (1378, "suite_id must need")

    CASE_NEED = (1379, "case_id must need")

    TEMPLATE_NAME_EXIST = (1380, "该ws下模板名字已存在")

    TEMPLATE_JOB_NEED_CASE = (1381, "模板创建任务之少有一个case")

    REPO_CHECK_FAIL = (1382, "仓库校验失败：")

    CHECK_NAME_FAIL = (1383, "check_name 错误")

    BRANCH_CHECK_FAIL = (1384, "branch不在仓库内")

    PRIORITY_FAIL = (1385, "优先级数字必须为1到100的整数")

    EDITOR_OBJ_ERROR = (1386, "编辑对象不在范围内")

    RELATION_ID_NEED = (1387, "relation_id is must need !")

    STOP_JOB_ERROR = (1388, "只允许停止running状态job")

    STOP_SUITE_ERROR = (1389, "只允许停止running状态SUITE")

    STOP_CASE_ERROR = (1340, "只允许停止running状态CASE")

    SKIP_CASE_ERROR = (1341, "只允许跳过pending状态CASE")

    DEFAULT_PROJECT_CAN_NOT_DELETE = (1342, "无法删除默认project")

    DEFAULT_PRODUCT_CAN_NOT_DELETE = (1343, "无法删除默认product")

    CREATOR_NEED = (500, "creator is required !")

    SUPPORT_POST = (500, "job create only support POST request !")

    TEMPLATE_DUPLICATION = (500, "template duplication")

    NO_PROJECT = (500, "project 不存在")

    NO_PRODUCT = (500, "product 不存在")

    TOKEN_ID_NEED = (1342, "token_id is must need !")

    PROJECT_NOT_EXISTS = (1343, "project name not exists !")

    BASELINE_NOT_EXISTS = (1344, "this ws baseline name not exists !")

    SUITE_NOT_EXISTS = (1345, "this ws suite name not exists !")

    CASE_NOT_EXISTS = (1346, "this ws case name not exists !")

    SERVER_NOT_EXISTS = (1347, "this ws server ip not exists !")

    SERVER_TAG_NOT_EXISTS = (1348, "this ws server tag not exists !")

    CLUSTER_NOT_EXISTS = (1349, "this ws cluster name not exists !")

    WS_NAME_NEED = (1350, " workspace  required !")

    WS_NOT_EXISTS = (1351, " workspace  not exists !")

    TEST_CASE_NEED = (1352, " test_case_id  必须传 !")

    START_TIME_NEED = (1353, " start_time  必须传 !")

    END_TIME_NEED = (1354, " end_time  必须传 !")

    METRIC_NEED = (1355, " metric  必须传 !")

    SUB_CASE_NEED = (1356, " sub_case  必须传 !")

    BASE_JOB_NEED = (1357, " base_group  必须传 !")

    COMPARE_LIST_NEED = (1358, " compare_groups  必须传 !")

    BASE_SUITE_OBJ_NEED = (1359, " base_suite_obj  必须传 !")

    REPORT_SOURCE_NEED = (1360, " report_source  必须传 !")

    TEST_ENV_NEED = (1361, " test_env  必须传 !")

    TEST_ITEM_NEED = (1362, " test_item  必须传 !")

    ITEM_NAME_NEED = (1363, " 测试项名字  必须传 !")

    SUITE_LIST_NEED = (1364, "测试项 suite_list  必须传 !")

    SHOW_TYPE_NEED = (1365, "show_type  必须传 !")

    CONF_LIST = (1366, "conf_list  必须传 !")

    REPORT_ID_NEED = (1367, "report_id  必须传 !")

    BUSINESS_TYPE_ERROR = (1368, "业务测试 business_type in (functional, performance, business) !")

    CASE_MACHINE_NUM_ERROR = (1369, "case_machine  数量错误 !")

    MONITOR_IP_OR_SN_ERROR = (1369, "监控配置 IP/SN错误 !")
