# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import logging
import colorlog

global_log_instance = list()


def get_logger(name='default'):
    logger = logging.getLogger(name)
    if name not in global_log_instance:
        console_handler = logging.StreamHandler()
        log_format = '\n'.join((
            '[%(levelname)s][%(asctime)s][%(process)d:%(thread)d]'
            '[%(filename)s:%(lineno)d %(funcName)s]: %(notice)s',
        ))
        color_log_format = '%(log_color)s' + log_format
        console_handler.setFormatter(colorlog.ColoredFormatter(color_log_format, log_colors={
            'DEBUG': 'blue',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red',
        }))
        logger.addHandler(console_handler)
        global_log_instance.append(name)
    return logger
