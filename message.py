import json
import logging
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tone.settings')
django.setup()

from tone.core.common.msg_notice import SimpleMsgHandle
from tone.services.notice.conf.constant import JobMessage, PlanMessage, MachineMessage, ReportMessage
from tone.services.notice.conf.constant import Topics
from tone.services.notice.core.consumer import ToneConsumer


class MessageProcessor(object):
    logger = logging.getLogger('message')

    @classmethod
    def _job_message_processor(cls, message):
        message_key = message.key.decode()
        message_value = json.loads(message.value.decode())
        message_obj = JobMessage(**message_value)
        ret = SimpleMsgHandle().job_handle(message_obj, message_key)
        cls.logger.info('message_key: {} | message_value: {} | result: {}'.
                        format(message_key, message_value, ret))

    @classmethod
    def _plan_message_processor(cls, message):
        message_key = message.key.decode()
        message_value = json.loads(message.value.decode())
        message_obj = PlanMessage(**message_value)
        ret = SimpleMsgHandle().plan_handle(message_obj, message_key)
        cls.logger.info('message_key: {} | message_value: {} | result: {}'.
                        format(message_key, message_value, ret))

    @classmethod
    def _machine_message_processor(cls, message):
        message_key = message.key.decode()
        message_value = json.loads(message.value.decode())
        message_obj = MachineMessage(**message_value)
        ret = SimpleMsgHandle().machine_handle(message_obj, message_key)
        cls.logger.info('message_key: {} | message_value: {} | result: {}'.
                        format(message_key, message_value, ret))

    @classmethod
    def _report_message_processor(cls, message):
        message_key = message.key.decode()
        message_value = json.loads(message.value.decode())
        message_obj = ReportMessage(**message_value)
        ret = SimpleMsgHandle().report_handle(message_obj, message_key)
        cls.logger.info('message_key: {} | message_value: {} | result: {}'.
                        format(message_key, message_value, ret))


class MessageDispatcher(MessageProcessor):
    @classmethod
    def _dispatch(cls, message):
        cls.logger.info('receive message:{}|{}|{}|{}|{}'.format(
            message.topic, message.offset, message.key, message.value, message.partition)
        )
        if message.topic == Topics.JOB_TOPIC:
            cls._job_message_processor(message)
        elif message.topic == Topics.PLAN_TOPIC:
            cls._plan_message_processor(message)
        elif message.topic == Topics.MACHINE_TOPIC:
            cls._machine_message_processor(message)
        elif message.topic == Topics.REPORT_TOPIC:
            cls._report_message_processor(message)


class MessageAcceptor(MessageDispatcher):
    @classmethod
    def run(cls):
        messages = cls._get_messages()
        for message in messages:
            cls._dispatch(message)

    @staticmethod
    def _get_messages():
        consumer = ToneConsumer().get_consumer()
        consumer.subscribe([Topics.JOB_TOPIC, Topics.PLAN_TOPIC, Topics.MACHINE_TOPIC, Topics.REPORT_TOPIC])
        return consumer


if __name__ == '__main__':
    MessageAcceptor.run()
