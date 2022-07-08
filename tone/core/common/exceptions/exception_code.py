"""
状态码	范围	        含义
2xx	    200-209     成功–表示请求已被成功接收、理解、接受
3xx	    300-309	    重定向–信息不完整需要进一步补充或者权限校验没有通过
4xx	    400-409	    客户端错误–请求有语法错误或请求无法实现
5xx	    500-509	    服务器端错误–服务器未能实现合法的请求
"""

SUCCESS_200 = {'code': 200, 'msg': 'success'}
PAGE_LIMIT_201 = {'code': 201, 'msg': 'Page Numbers exceed maximum limits'}
DELETE_WS_EXISTS_201 = {'code': 201, 'msg': '注销申请正在审批中，请等待'}
FIELD_REQUIRED_202 = {'code': 202, 'msg': 'The field is required. Please check the parameters'}
DATA_EXISTS_203 = {'code': 203, 'msg': 'The data already exists in the database. Please reenter and submit'}
PARAM_ERROR_204 = {'code': 204, 'msg': 'Parameter error. Please reenter and submit'}

SERVER_ERROR_500 = {'code': 500, 'msg': 'Server error, please contact administrator'}
SERVER_TIMEOUT_504 = {'code': 504, 'msg': 'Server response timeout, please try again later'}
STARAGENT_ERROR_511 = {'code': 511, 'msg': 'star-agent error'}
TONEAGENT_ERROR_512 = {'code': 512, 'msg': 'tone-agent error'}
ALIYUN_ERROR_513 = {'code': 513, 'msg': 'aliyun api error'}
