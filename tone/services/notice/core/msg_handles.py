import json

import requests
from django.core.mail import EmailMultiAlternatives

from tone import settings


class EmailMessageHandle(object):
    @classmethod
    def send(cls, subject, content, send_to, cc_to=None, bcc_to=None):
        if not isinstance(send_to, (list, tuple)):
            send_to = [send_to]
        if cc_to and not isinstance(cc_to, (list, tuple)):
            cc_to = [cc_to]
        if bcc_to and not isinstance(bcc_to, (list, tuple)):
            bcc_to = [bcc_to]
        email = EmailMultiAlternatives(
            subject,
            content,
            settings.EMAIL_HOST_USER,
            send_to,
            cc=cc_to,
            bcc=bcc_to
        )
        email.attach_alternative(content, 'text/html')
        email.send()
        return True


class DingTalkMessageHandle(object):

    def __init__(self, url=None, headers=None):
        self.url = 'https://oapi.dingtalk.com/robot/send' if not url else url
        self.headers = {'Content-type': 'application/json', 'Accept': 'application/json'} if not headers else headers

    def _send(self, json_data, token):
        req = requests.post(self.url,
                            headers=self.headers,
                            data=json.dumps(json_data),
                            params={'access_token': token}
                            )
        return req.json()

    def send_markdown_message(self, subject, content, token):
        msg_data = {
            'msgtype': 'markdown',
            'markdown': {
                'title': subject,
                'text': content
            }
        }
        return self._send(msg_data, token)

    def send_link_message(self, subject, content, link_url, pic_url, token):
        msg_data = {
            'msgtype': 'link',
            'link': {
                'title': subject,
                'text': content,
                'messageUrl': link_url,
                'picUrl': pic_url
            }
        }
        return self._send(msg_data, token)

    def send_text_message(self, content, token, at=[], at_all=False):
        msg_data = {
            'msgtype': 'text',
            'text': {
                'content': content
            }
        }
        if at or at_all:
            if not isinstance(at, list):
                at = [at]
            msg_data['at'] = {
                'atMobiles': at,
                'isAtAll': at_all
            }
        return self._send(msg_data, token)
