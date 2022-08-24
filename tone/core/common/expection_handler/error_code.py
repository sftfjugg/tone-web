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

    KERNEL_NAME_LACK = (1203, "缺少参数kernel name")

    KERNEL_VERSION_LACK = (1204, "缺少参数kernel version")

    KERNEL_PACKAGE_LACK = (1205, "缺少参数kernel_link, devel_link, headers_link")

    KERNEL_ID_LACK = (1206, "缺少参数kernel_id")

    KERNEL_VERSION_DUPLICATION = (1207, "已存在同名version")

    TAG_NONEXISTENT = (1301, "该workspace下tag不存在")

    TAG_DUPLICATION = (1302, "已存在同名tag")

    TYPE_NONEXISTENT = (1303, "job_type不存在")

    TYPE_DUPLICATION = (1304, "已存在同名job_type")

    TYPE_ID_LACK = (1305, "缺少参数job_type id")

    ITEM_NONEXISTENT = (1306, "job_type的原子项不存在")

    SYS_TYPE_ATOMIC = (1307, "系统类型无法删除")

    ITEM_MUST_DIC = (1308, "参数item_dic类型应该是dict")

    SERVER_TYPE_LACK = (1309, "缺少参数server_type")

    TEST_TYPE_LACK = (1310, "缺少参数test_type")

    TAG_ID_NEED = (1311, "缺少参数tag_id")

    TEST_JOB_NONEXISTENT = (1351, "Job不存在")

    TEST_CONF_NEED = (1352, "缺少参数test_config")

    TEST_CONF_LIST = (1353, "参数test_config类型应该是list")

    TEST_SUITE_NEED = (1354, "缺少参数test_suite_id")

    TEST_SUITE_NAME_NEED = (1354, "缺少参数test_suite_name")

    CASES_LIST = (1354, "参数cases_list类型应该是list")

    SERVER_NONEXISTENT = (1355, "workspace下机器不存在")

    SERVER_STATUS = (1356, "指定机器Broken，请检查指定机器是否可用")

    CLUSTER_NO_SERVER = (1357, "集群无关联机器")

    SERVER_TYPE_MUTEX = (1358, "case server_object_id customer_server server_tag_id mutex!")

    DATA_FORM_ERROR = (1359, "data_from 参数有误 !")

    CONFIG_ID_NEED = (1360, "缺少参数config!")

    CONFIG_NONEXISTENT = (1361, "config不存在")

    CONFIG_DUPLICATION = (1362, "已存在同名config")

    CONFIG_KEY_NEED = (1363, "config_key 必须传")

    CONFIG_TYPE_NEED = (1364, "缺少参数config_type")

    TEST_TEMPLATE_NONEXISTENT = (1365, "TestTemplate不存在")

    TEMPLATE_NEED = (1366, "缺少参数template_id")

    DEFAULT_DUPLICATION = (1367, "同一workspace下默认job_type唯一")

    PRODUCT_DUPLICATION = (1368, "workspace下已存在同名product")

    PRODUCT_ID_NEED = (1369, "缺少参数prd_id!")

    PRODUCT_NEED = (1370, "缺少参数product_id")

    PROJECT_DUPLICATION = (1371, "已存在同名project")

    PRODUCT_VERSION_DUPLICATION = (1390, "已存在同名产品版本")

    PRODUCT_VERSION_NEED = (1391, "产品版本必传")

    PROJECT_ID_NEED = (1372, "缺少参数project_id!")

    GIT_URL_NEED = (1373, "缺少参数git_url")

    REPOSITORY_DUPLICATION = (1374, "project下已存在同名仓库")

    REPOSITORY_ID_NEED = (1375, "缺少参数repository_id!")
    BRANCH_DUPLICATION = (1376, "仓库下已存在同名branch")

    BRANCH_ID_NEED = (1377, "缺少参数branch_id!")

    SUITE_NEED = (1378, "缺少参数suite_id")

    CASE_NEED = (1379, "缺少参数case_id")

    TEMPLATE_NAME_EXIST = (1380, "该ws下模板名字已存在")

    TEMPLATE_JOB_NEED_CASE = (1381, "模板创建任务之少有一个case")

    REPO_CHECK_FAIL = (1382, "仓库校验失败：")

    CHECK_NAME_FAIL = (1383, "check_name 错误")

    BRANCH_CHECK_FAIL = (1384, "branch不在仓库内")

    PRIORITY_FAIL = (1385, "优先级数字必须为1到100的整数")

    EDITOR_OBJ_ERROR = (1386, "编辑对象不在范围内")

    RELATION_ID_NEED = (1387, "缺少参数relation_id!")

    STOP_JOB_ERROR = (1388, "只允许停止running状态job")

    STOP_SUITE_ERROR = (1389, "只允许停止running状态SUITE")

    STOP_CASE_ERROR = (1340, "只允许停止running状态CASE")

    SKIP_CASE_ERROR = (1341, "只允许跳过pending状态CASE")

    DEFAULT_PROJECT_CAN_NOT_DELETE = (1342, "无法删除默认project")

    DEFAULT_PRODUCT_CAN_NOT_DELETE = (1343, "无法删除默认product")

    CREATOR_NEED = (500, "缺少参数creator!")

    SUPPORT_POST = (500, "job create only support POST request !")

    TEMPLATE_DUPLICATION = (500, "template duplication")

    NO_PROJECT = (500, "project 不存在")

    NO_PRODUCT = (500, "product 不存在")

    TOKEN_ID_NEED = (1342, "缺少参数token_id!")

    PROJECT_NOT_EXISTS = (1343, "project name不存在!")

    BASELINE_NOT_EXISTS = (1344, "该workspace下baseline name不存在!")

    SUITE_NOT_EXISTS = (1345, "该workspace下suite name不存在!")

    CASE_NOT_EXISTS = (1346, "该workspace下case name不存在!")

    SERVER_NOT_EXISTS = (1347, "该workspace下server ip不存在!")

    SERVER_TAG_NOT_EXISTS = (1348, "该workspace下server tag不存在!")

    CLUSTER_NOT_EXISTS = (1349, "该workspace下cluster name不存在!")

    WS_NAME_NEED = (1350, "缺少参数workspace!")

    WS_NOT_EXISTS = (1351, " workspace  not exists !")

    TEST_CASE_NEED = (1352, "缺少参数test_case_id!")

    START_TIME_NEED = (1353, "缺少参数start_time!")

    END_TIME_NEED = (1354, "缺少参数end_time!")

    METRIC_NEED = (1355, "缺少参数metric!")

    SUB_CASE_NEED = (1356, "缺少参数sub_case!")

    BASE_JOB_NEED = (1357, "缺少参数base_group!")

    COMPARE_LIST_NEED = (1358, "缺少参数compare_groups!")

    BASE_SUITE_OBJ_NEED = (1359, "缺少参数base_suite_obj!")

    REPORT_SOURCE_NEED = (1360, "缺少参数report_source!")

    TEST_ENV_NEED = (1361, "缺少参数test_env!")

    TEST_ITEM_NEED = (1362, "缺少参数test_item!")

    ITEM_NAME_NEED = (1363, "缺少参数测试项名字!")

    SUITE_LIST_NEED = (1364, "缺少参数测试项 suite_list!")

    SHOW_TYPE_NEED = (1365, "缺少参数show_type!")

    CONF_LIST = (1366, "缺少参数conf_list!")

    REPORT_ID_NEED = (1367, "缺少参数report_id!")

    BUSINESS_TYPE_ERROR = (1368, "业务测试 business_type in (functional, performance, business) !")

    CASE_MACHINE_NUM_ERROR = (1369, "case_machine  数量错误 !")

    MONITOR_IP_OR_SN_ERROR = (1369, "监控配置 IP/SN错误 !")

    AK_NOT_CORRECT = (1370, "AK错误")

    SERVER_NOT_IN_THIS_WS = (1371, "该机器不在当前workspace机器池中")

    SERVER_USED_BY_OTHER_WS = (1372, "该机器已在其他workspace中使用")

    CONF_NAME_NOT_EXISTS = (1374, "test_suite下没有该test_conf!")

    SUITE_NAME_NOT_EXISTS = (1375, "该test_suite不存在!")

    JOB_ID_NOT_EXISTS = (1376, "该job_id不存在!")

    JOB_SUITE_NAME_NOT_EXISTS = (1377, "job_id对应的任务中没有该test_suite!")

    JOB_CONF_NAME_NOT_EXISTS = (1378, "job_id对应的任务中没有该test_conf!")

    ADD_SERVER_TO_TONEAGENT_FAILED = (1379, "添加机器至ToneAgent系统失败")
    SERVER_TSN_ALREADY_EXIST = (1380, "该机器在系统中已存在")
