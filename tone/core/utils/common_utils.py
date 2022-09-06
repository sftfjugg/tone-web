import re
import shlex

from tone.core.common.expection_handler.custom_error import JobTestException
from tone.core.common.expection_handler.error_code import ErrorCode


def list_shlex_data(shlex_data, list_equal_sign, list_equal_sign_index, list_connect_equal_sign_tuple,
                    list_comma_index, list_shlex_data, env_data_list):
    if shlex_data.count('=') == 1:
        env_data_list.append(shlex_data)
    else:
        for equal in re.finditer('=', shlex_data):
            tuple_equal_sign = equal.span()
            list_equal_sign.append(tuple_equal_sign)
        for equal_sign in list_equal_sign:
            list_equal_sign_index.append(equal_sign[0])
        for equal_sign_index in range(len(list_equal_sign_index)):
            if equal_sign_index + 1 >= len(list_equal_sign_index):
                break
            list_connect_equal_sign_tuple.append((list_equal_sign_index[equal_sign_index],
                                                  list_equal_sign_index[equal_sign_index + 1]))
        for connect_equal_sign_tuple in list_connect_equal_sign_tuple:
            comma_index = shlex_data.rfind(',', connect_equal_sign_tuple[0], connect_equal_sign_tuple[1])
            list_comma_index.append(comma_index)
        list_comma_index.append(len(shlex_data))
        count = 0
        for k in range(len(list_comma_index)):
            if k + 1 >= len(list_comma_index):
                break
            if count != 0:
                list_shlex_data.append(shlex_data[(list_comma_index[k] + 1):list_comma_index[k + 1]])
            else:
                list_shlex_data.append(shlex_data[list_comma_index[k]:list_comma_index[k + 1]])
            count += 1
    return list_shlex_data


def pack_env_infos(data):
    """
    组装env_info
    """
    list_equal_sign = []
    list_equal_sign_index = []
    list_connect_equal_sign_tuple = []
    list_comma_index = [0]
    list_shlex_data_list = []
    if not data:
        return dict()
    env_data = dict()
    env_data_list = []
    try:
        shlex_data_list = shlex.split(data)
        for shlex_data in shlex_data_list:
            list_shlex_data_list = list_shlex_data(shlex_data, list_equal_sign, list_equal_sign_index,
                                                   list_connect_equal_sign_tuple, list_comma_index,
                                                   list_shlex_data_list, env_data_list)
        for shlex_data_l in list_shlex_data_list:
            env_data_list.append(shlex_data_l)
        for env_data_l in env_data_list:
            item = env_data_l.split('=', 1)
            if ' ' in item[1] and "'" not in item[1]:
                env_data[item[0]] = "'" + item[1] + "'"
            elif ' ' in item[1] and '"' not in item[1]:
                env_data[item[0]] = '"' + item[1] + '"'
            else:
                env_data[item[0]] = item[1]
    except Exception:
        raise JobTestException(ErrorCode.GLOBAL_VARIABLES_ERROR)
    return env_data