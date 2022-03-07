import logging

from tone.celery import app
from tone.models import OutSiteMsg
from tone.services.notice.conf.constant import DingTalkMessageChoices, SendByChoices
from tone.services.notice.core.msg_handles import DingTalkMessageHandle, EmailMessageHandle

logger = logging.getLogger('schedule')


def send_message():
    messages = OutSiteMsg.objects.filter(is_send=False)
    for message in messages:
        if message.send_by == SendByChoices.DING_TALK:
            send_ding_message(message.id)
        elif message.send_by == SendByChoices.EMAIL:
            send_email_message(message.id)
        else:
            return
        message.is_send = True
        OutSiteMsg.objects.filter(id=message.id).update(is_send=True)


# @app.task
def send_ding_message(message_id):
    message = OutSiteMsg.objects.get(id=message_id)
    handle = DingTalkMessageHandle()
    token_list = message.send_to.strip().split(',')
    for token in token_list:
        if not token:
            return
        if message.send_type == DingTalkMessageChoices.MARKDOWN:
            ret = handle.send_markdown_message(message.subject, message.content, token)
        elif message.send_type == DingTalkMessageChoices.LINK:
            ret = handle.send_link_message(message.subject, message.content, message.msg_link,
                                           message.msg_pic, token)
        else:
            ret = handle.send_text_message(message.content, token)
        logger.info('send dingtalk message. id:{} | type:{} | result:{}'.format(message.id, message.send_type, ret))


# @app.task
def send_email_message(message_id):
    message = OutSiteMsg.objects.get(id=message_id)
    send_to = message.send_to.strip().split(',')
    cc_to = message.cc_to.strip().split(',')
    bcc_to = message.bcc_to.strip().split(',')
    ret = EmailMessageHandle.send(message.subject, message.content, send_to, cc_to, bcc_to)
    logger.info('send email message. id:{} | result:{}'.format(message.id, ret))
