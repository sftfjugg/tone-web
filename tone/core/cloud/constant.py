DEFAULT_VPC_CIDR_BLOCK = '172.16.0.0/16'
DEFAULT_VSWITCH_CIDR = '172.16.0.0/24'
DEFAULT_VPC_NAME = 'OSTestDefaultVPC'
DEFAULT_VSWITCH_NAME = 'OSTestDefaultVSWITCH'
DEFAULT_EIP_NAME = 'OSTestDefaultEIP'


WORK_ACCESS_CIDR_BLOCK_LIST = [
    '0.0.0.0/0'
]

SECURITY_GROUP_DROP_CIDR_BLOCK_LIST = []


class CloudServerStatus(object):
    NORMAL = 0
    RELEASE = 1


class TestType(object):
    FUNCTIONAL = 'functional'
    PERFORMANCE = 'performance'
