import json

from tone import settings


class Servers:
    SERVERS_LIST = json.loads(settings.KAFKA_SERVERS_LIST)


class Topics:
    JOB_TOPIC = 'tone-job-topic'
    PLAN_TOPIC = 'tone-plan-topic'
    MACHINE_TOPIC = 'tone-machine-topic'
    REPORT_TOPIC = 'tone-report-topic'


class Groups:
    JOB_GROUP = 'tone-job-group'
    PLAN_GROUP = 'tone-plan-group'
    MACHINE_GROUP = 'tone-machine-group'
    REPORT_GROUP = 'tone-report-group'


class MachineType:
    ALIGROUP = 'aligroup'
    ALIYUN = 'aliyun'


class MachineState:
    BROKEN = 'broken'


class SendByChoices:
    DING_TALK = 'ding_talk'
    EMAIL = 'email'


class DingTalkMessageChoices:
    LINK = 'link'
    MARKDOWN = 'markdown'


class JobMessage:
    def __init__(self, **kwargs):
        self.job_id = kwargs.get('job_id')
        self.job_state = kwargs.get('state')


class PlanMessage:
    def __init__(self, **kwargs):
        self.plan_id = kwargs.get('plan_id')
        self.plan_inst_id = kwargs.get('plan_inst_id')
        self.plan_state = kwargs.get('plan_state')


class MachineMessage:
    def __init__(self, **kwargs):
        self.machine_id = kwargs.get('machine_id')
        self.impact_job = kwargs.get('impact_job')
        self.impact_suite = kwargs.get('impact_suite', list())
        self.machine_type = kwargs.get('machine_type', MachineType.ALIGROUP)
        self.state = kwargs.get('state', MachineState.BROKEN)
        self.in_pool = kwargs.get('in_pool', True)


class ReportMessage:
    def __init__(self, **kwargs):
        self.job_id = kwargs.get('job_id')
