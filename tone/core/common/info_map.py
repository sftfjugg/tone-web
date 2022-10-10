from tone.core.common.constant import RESULT_INFO_MAP, LINK_INFO_LIST


def get_result_map(step, msgs):
    """后端提示信息返回前端前做映射处理"""
    if not msgs:
        return msgs
    maps = RESULT_INFO_MAP.get(step)
    for key, info in maps.items():
        if key in msgs:
            return info
        elif "***" in key:
            if all([i in msgs for i in key.split("***")]):
                if "%s" in info:
                    return info % msgs.rstrip(",").rstrip(".")
                else:
                    return info
    return msgs


def add_link_msg(msg):
    """返回信息中关键字增加超链接"""
    if not msg:
        return
    for info in LINK_INFO_LIST:
        if info in msg:
            return info
    return None
