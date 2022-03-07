import json

from kafka import KafkaProducer

from tone.services.notice.conf.constant import Servers, Topics
from tone.services.notice.conf.settings import api_version, retries


class ToneProducer(object):

    @staticmethod
    def get_producer():
        return KafkaProducer(
            bootstrap_servers=Servers.SERVERS_LIST,
            api_version=api_version,
            retries=retries,
        )

    def send(self, topic_name, msg_value, msg_key=None):
        if isinstance(msg_key, str):
            msg_key = msg_key.encode()
        producer = self.get_producer()
        try:
            future = producer.send(topic_name, msg_value, key=msg_key)
            result = future.get()
            print(result)
            return 200, result
        except Exception as e:
            print('send notice failed.')
            print(e)
            return 500, str(e)


if __name__ == '__main__':
    # test
    p = ToneProducer()
    data = {
        'job_id': 606,
        'status': 'success'
    }
    p.send(Topics.JOB_TOPIC, json.dumps(data).encode(), msg_key='job_state_change')