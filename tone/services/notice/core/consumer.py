from kafka import KafkaConsumer

from tone.services.notice.conf import settings
from tone.services.notice.conf.constant import Servers, Groups, Topics


class ToneConsumer(object):
    @staticmethod
    def get_consumer():
        return KafkaConsumer(
            bootstrap_servers=Servers.SERVERS_LIST,
            group_id=Groups.JOB_GROUP,
            api_version=settings.api_version,
            session_timeout_ms=settings.session_timeout_ms,
            max_poll_records=settings.max_poll_records,
            fetch_max_bytes=settings.fetch_max_bytes
        )


if __name__ == '__main__':
    consumer = ToneConsumer().get_consumer()
    consumer.subscribe([Topics.JOB_TOPIC, Topics.PLAN_TOPIC, Topics.MACHINE_TOPIC, Topics.REPORT_TOPIC])
    for message in consumer:
        print(message.value, message.key)
