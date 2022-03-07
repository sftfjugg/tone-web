import re


def check_ip(ipAddr):
    compile_ip = re.compile(
        '^(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|[1-9])\.(1\d{2}'
        '|2[0-4]\d|25[0-5]|[1-9]\d|\d)\.(1\d{2}|2[0-4]\d|25[0-5]'
        '|[1-9]\d|\d)\.(1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)$')

    if compile_ip.match(ipAddr):
        return True
    else:
        return False


def check_contains_chinese(string):
    for _char in string:
        if '\u4e00' <= _char <= '\u9fa5':
            return True
    return False
