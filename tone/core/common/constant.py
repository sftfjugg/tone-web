import re

from tone import settings

SCRIPT_FLAG = 'script'

IP_PATTEN = re.compile(r'^(\d+\.\d+\.\d+\.\d+)')


class EnvType(object):
    PRE = 'pre'
    PROD = 'prod'
    DAILY = 'daily'
    LOCAL = 'local'

    @classmethod
    def is_test(cls):
        return True if settings.ENV_TYPE in ['local', 'daily'] else False

    @classmethod
    def is_local(cls):
        return settings.ENV_TYPE == 'local'

    @classmethod
    def cur_domain(cls):
        return 'https://tone.aliyun.test' if cls.is_test() else 'https://tone.aliyun-inc.com'


class EnvMode(object):
    ALI = 'ali'
    OPENANOLIS = 'openanolis'
    STANDALONE = 'standalone'


DEFAULT_DOMAIN = '其他'

SUITE_STEP_STAGE_MAP = {
    'script_before_suite': 'setup',
    'script_after_suite': 'teardown',
    'suite_monitor': 'monitor',
    'reboot_before_suite': 'reboot',
    'run_case': 'run_case',
}

SUITE_STEP_PREPARE_MAP = {
    'script_before_suite': 'setup',
    'script_after_suite': 'teardown',
    'suite_monitor': 'monitor',
    'reboot_before_suite': 'reboot',
}

CASE_STEP_STAGE_MAP = {
    'script_before_case': 'setup',
    'script_after_case': 'teardown',
    'case_monitor': 'monitor',
    'reboot_before_case': 'reboot',
    # 'run_case': 'run_case',
}

PREPARE_STEP_STAGE_MAP = {
    'init_cloud': 'init_cloud',
    'initial': 'initial',
    're_clone': 're_clone',
    'reboot': 'reboot',
    'install_rpm_before_reboot': 'install_rpm',
    'script_before_reboot': 'script',
    'script_before_install_kernel': 'script',
    'install_kernel': 'install_kernel',
    'install_hotfix': 'install_hotfix',
    'script_after_install_kernel': 'script',
    'reboot_for_install_kernel': 'reboot',
    'script_after_reboot': 'script',
    'install_rpm_after_reboot': 'install',
    'job_console': 'console',
    'prepare': 'prepare',
    'check_kernel_install': 'check_kernel_install',
}

FUNC_CASE_RESULT_TYPE_MAP = {
    1: 'Pass',
    2: 'Fail',
    3: 'Conf',
    4: 'Block',
    5: 'Skip',
    6: 'Warning'
}

PERF_CASE_RESULT_TYPE_MAP = {
    'increase': '上升',
    'decline': '下降',
    'normal': '正常',
    'invalid': '无效值',
    'na': 'NA',
    '': '-',
}

BIND_STAGE = {
    'reboot': '重启',
    'ssh_pub_key': '生成RSA密钥',
    'initial': '初始化',
    'install_kernel': '安装内核',
    'install_rpm': '安装rpm',
    'install_hotfix': '安装hotfix',
    'prepare': '准备',
    'upload': '上传文件',
    'run_test': '执行测试',
}

YUM_PACKAGE_REPOSITORY_URL = 'http://yum.tbsite.net'
KERNEL_URL = "http://yum.tbsite.net/taobao/7/x86_64/"

TEST_SUITE_REDIS_KEY = 'tone-test_suites'
FUNCTIONAL = 'functional'
PERFORMANCE = 'performance'
BUSINESS = 'business'
STABILITY = 'stability'

# TestFarm 地址
DAILY_SITE_URL = 'https://testone.aliyun.test/'
PROD_SITE_URL = 'http://testfarm.opencoral.cn/'

WS_LOGO_DIR = '/wslogo'
DOC_IMG_DIR = '/docimg'
OFFLINE_DATA_DIR = '/offline'
RESULTS_DATA_DIR = '/results'
RANDOM_THEME_COLOR_LIST = [
    '#FF9D4E', '#39B3B2', '#5B8FF9', '#F56C6C', '#3FB7E6'
]

ANALYSIS_SQL_MAP = {
    'group_perf': """
        SELECT
        A.id,
        A.name,
        A.start_time,
        A.end_time,
        A.build_pkg_info,
        E.first_name,
        E.last_name,
        D.ip,
        B.test_value,
        B.cv_value, 
        B.note,
        B.id,
        C.id,
        C.run_mode,
        E.id,
        D.id
    FROM
        test_job AS A,
        perf_result AS B,
        test_job_case AS C,
        test_server_snapshot AS D,
        user AS E,
        job_tag AS F,
        job_tag_relation AS G 
    WHERE
        A.id = B.test_job_id 
        AND A.start_time >= '{start_time}'
        AND A.end_time <= '{end_time}'
        AND A.server_provider = '{provider_env}'
        AND A.test_type = 'performance' 
        AND A.project_id = {project} 
        AND B.metric = '{metric}' 
        AND C.job_id = A.id 
        AND B.test_case_id = C.test_case_id 
        AND C.test_case_id = {test_case} 
        AND B.test_suite_id = C.test_suite_id 
        AND C.test_suite_id = {test_suite} 
        AND C.state IN ( 'success', 'fail' ) 
        AND A.state IN ( 'success', 'fail' ) 
        AND C.server_snapshot_id = D.id 
        AND A.creator = E.id
        AND A.is_deleted = 0
        AND B.is_deleted = 0
        AND C.is_deleted = 0
        AND D.is_deleted = 0
        AND F.is_deleted = 0
        AND G.is_deleted = 0
        AND F.ws_id = A.ws_id 
        AND F.NAME = 'analytics' 
        AND F.id = G.tag_id 
        AND A.id = G.job_id
    """,
    'group_perf_tag': """
    SELECT
        A.id,
        A.name,
        A.start_time,
        A.end_time,
        A.build_pkg_info,
        E.first_name,
        E.last_name,
        D.ip,
        B.test_value,
        B.cv_value,
        B.note,
        B.id,
        C.id,
        C.run_mode,
        E.id,
        D.id
    FROM
        test_job AS A,
        perf_result AS B,
        test_job_case AS C,
        test_server_snapshot AS D,
        user AS E,
        job_tag_relation AS F, 
        job_tag AS G, 
        job_tag_relation AS H
    WHERE
        A.id = B.test_job_id 
        AND A.start_time >= '{start_time}'
        AND A.end_time <= '{end_time}'
        AND A.server_provider = '{provider_env}'
        AND A.test_type = 'performance' 
        AND A.project_id = {project} 
        AND B.metric = '{metric}' 
        AND C.job_id = A.id 
        AND B.test_case_id = C.test_case_id 
        AND C.test_case_id = {test_case} 
        AND B.test_suite_id = C.test_suite_id 
        AND C.test_suite_id = {test_suite} 
        AND C.state IN ( 'success', 'fail' ) 
        AND A.state IN ( 'success', 'fail' ) 
        AND C.server_snapshot_id = D.id 
        AND A.creator = E.id 
        AND F.job_id = A.id 
        AND F.tag_id = {tag}
        AND A.is_deleted = 0
        AND B.is_deleted = 0
        AND C.is_deleted = 0
        AND D.is_deleted = 0
        AND F.is_deleted = 0
        AND G.is_deleted = 0
        AND H.is_deleted = 0
        AND G.ws_id = A.ws_id 
        AND G.NAME = 'analytics' 
        AND G.id = H.tag_id 
        AND A.id = H.job_id
   """,
    'group_perf_aliyun': """
    SELECT
        A.id,
        A.NAME,
        A.start_time,
        A.end_time,
        A.build_pkg_info,
        E.first_name,
        E.last_name,
        D.private_ip,
        B.test_value,
        B.cv_value,
        B.note,
        B.id,
        D.instance_type,
        D.image,
        D.bandwidth,
        C.run_mode,
        C.id,
        E.id,
        D.id
    FROM
        test_job AS A,
        perf_result AS B,
        test_job_case AS C,
        cloud_server_snapshot AS D,
        user AS E,
        job_tag AS F,
        job_tag_relation AS G  
    WHERE
        A.id = B.test_job_id 
        AND A.start_time >= '{start_time}'
        AND A.end_time <= '{end_time}'
        AND A.server_provider = '{provider_env}'
        AND A.test_type = 'performance'
        AND A.project_id = {project} 
        AND B.metric = '{metric}'
        AND C.job_id = A.id 
        AND B.test_case_id = C.test_case_id 
        AND C.test_case_id = {test_case} 
        AND B.test_suite_id = C.test_suite_id 
        AND C.test_suite_id = {test_suite} 
        AND C.state IN ( 'success', 'fail' ) 
        AND A.state IN ( 'success', 'fail' ) 
        AND C.server_snapshot_id = D.id 
        AND A.creator = E.id
        AND A.is_deleted = 0
        AND B.is_deleted = 0
        AND C.is_deleted = 0
        AND D.is_deleted = 0
        AND F.is_deleted = 0
        AND G.is_deleted = 0
        AND F.ws_id = A.ws_id 
        AND F.NAME = 'analytics' 
        AND F.id = G.tag_id 
        AND A.id = G.job_id
    """,
    'group_perf_aliyun_tag': """
    SELECT
        A.id,
        A.NAME,
        A.gmt_created,
        A.gmt_modified,
        A.build_pkg_info,
        E.first_name,
        E.last_name,
        D.private_ip,
        B.test_value,
        B.cv_value,
        B.note,
        B.id,
        D.instance_type,
        D.image,
        D.bandwidth,
        C.run_mode,
        C.id,
        E.id,
        D.id
    FROM
        test_job AS A,
        perf_result AS B,
        test_job_case AS C,
        cloud_server_snapshot AS D,
        USER AS E,
        job_tag_relation AS F,
        job_tag AS G, 
        job_tag_relation AS H
    WHERE
        A.id = B.test_job_id 
        AND A.start_time >= '{start_time}'
        AND A.end_time <= '{end_time}'
        AND A.server_provider = '{provider_env}'
        AND A.test_type = 'performance' 
        AND A.project_id = {project} 
        AND B.metric = '{metric}' 
        AND C.job_id = A.id 
        AND B.test_case_id = C.test_case_id 
        AND C.test_case_id = {test_case} 
        AND B.test_suite_id = C.test_suite_id 
        AND C.test_suite_id = {test_suite} 
        AND C.state IN ( 'success', 'fail' ) 
        AND A.state IN ( 'success', 'fail' ) 
        AND C.server_snapshot_id = D.id 
        AND A.creator = E.id 
        AND F.job_id = A.id 
        AND F.tag_id = {tag}
        AND A.is_deleted = 0
        AND B.is_deleted = 0
        AND C.is_deleted = 0
        AND D.is_deleted = 0
        AND F.is_deleted = 0
        AND G.is_deleted = 0
        AND H.is_deleted = 0
        AND G.ws_id = A.ws_id 
        AND G.NAME = 'analytics' 
        AND G.id = H.tag_id 
        AND A.id = H.job_id
""",

}

FILTER_JOB_TAG_SQL = """
    SELECT DISTINCT
        A.id 
    FROM
        test_job AS A,
        job_tag AS B,
        job_tag_relation AS C 
    WHERE
        A.project_id = {project_id}
        AND B.NAME = 'analytics' 
        AND B.id = C.tag_id 
        AND A.id = C.job_id 
        AND A.is_deleted = 0 
        AND B.is_deleted = 0 
        AND C.is_deleted = 0 
    ORDER BY
        A.id DESC
        LIMIT 30
"""

JOB_MONITOR_ITEM = ['cpu', 'disk', 'diskio', 'kernel', 'mem', 'swap', 'system', 'cgroup', 'kernel_vmstat', 'net',
                    'netstat', 'nstat', 'processes', 'interrupts', 'linux_sysctl_fs']


class MonitorType:
    CASE_MACHINE = 'case_machine'
    CUSTOM_MACHINE = 'custom_machine'


SERVER_REAL_STATE_RETURN_MAP = {'Available': 'Online', 'Broken': 'Offline'}
SERVER_REAL_STATE_PUT_MAP = {'Online': 'Available', 'Offline': 'Broken'}
# 机器“心跳状态”由数据库存储的实际状态的Available改成Online；Broken改成Offline

# 提示信息中需要前端增加超链接的文字
LINK_INFO_LIST = ["T-One开发"]

# 后端返回提示信息与前台提示信息映射表
RESULT_INFO_MAP = {
    "output_result": {
        "run case done": "Completed",
        "script exec failed(signal: killed)": "Script exec failed(signal: killed), please check the timeout "
                                              "configuration in Test Suite management.",
        "task sent successfully, but executing timeout": "Execution timeout, please check the timeout configuration "
                                                         "in Test Suite management.",
        "tone install *** error": "%s, please enter the machine to check the relevant log in the /tmp directory.",
        "run ***:*** failed": "run case failed, please enter the machine to check the relevant log in the /tmp "
                              "directory."
    },
    "test_prepare": {
        "tone make install error": "tone make install error, please enter the machine to check the prepare_tone.log "
                                   "in the /tmp directory.",
        "clone tone from *** failed": "Failed to clone tone repo, please check machine network and proxy, or enter "
                                      "the machine to check the prepare_tone.log in the /tmp directory.",
        "Failed to ***": "%s, please enter the machine to check the relevant log in the /tmp directory.",
    },
    "add_machine": {
        "***No space left on device***": "磁盘空间不足，请清理磁盘空间后重新添加。"
    }
}
