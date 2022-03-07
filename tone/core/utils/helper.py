import functools
import json
from datetime import datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse

from tone.core.utils.date_util import DateUtil


class Singleton(object):
    _instance = None

    @classmethod
    def get_instance(cls, *args, **kwargs):
        if cls._instance:
            result = cls._instance
        else:
            result = cls(*args, **kwargs)
            cls._instance = result
        return result


def singleton(cls):
    instances = {}

    @functools.wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


class CommResp(object):
    def __init__(self):
        self.result = True
        self.data = None
        self.msg = 'ok'
        self.code = 200

    def to_json(self):
        final_result = {'success': self.result,
                        'msg': self.msg,
                        'data': self.data,
                        'code': self.code}
        if hasattr(self, 'total'):
            final_result['total'] = self.total
        return json.dumps(final_result, indent=4, cls=DjangoJSONEncoder, ensure_ascii=False)

    def json_resp(self):
        return HttpResponse(self.to_json(), content_type='application/json')


class CommonResponse(object):
    def __init__(self, result=False, data=None, msg=''):
        self.result = result
        self.data = data if data else []
        self.msg = msg

    def to_show(self, others=None):
        result = {'success': self.result, 'msg': self.msg, 'data': self.data}
        if not others:
            others = ('total',)
        for other in others:
            if hasattr(self, other):
                result[other] = getattr(self, other)
        return result

    def update(self, **args):
        for k, v in args.items():
            if v is not None:
                setattr(self, k, v)


class ObjectDict(dict):
    def __str__(self):
        return dict(self).__str__()

    def __repr__(self):
        return self.__str__()

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, d):
        self.__dict__.update(d)

    def __getattr__(self, attr):
        value = self[attr]
        return ObjectDict(value) if isinstance(value, dict) else value

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        del self[name]


class MarkdownTable(object):
    def __init__(self, column=None, row=None, data=None):
        """
        :param column:
        :type column: list
        :param row:
        :type row: list[list]
        :param data:
        :type data: list[list]
        """
        self.column = column or []
        self.row = row or [[]]
        self.data = data or [[]]

    def _add_split_sign(self, item):
        """
        对给定的list，添加分隔符
        :param item: 要分割的列表
        :type item: list
        :rtype: str
        """
        # 所有制为str类型
        item = map(lambda x: str(x), item)
        middle = " | ".join(item)
        return "| " + middle + " |"

    def _generate_title(self, pos):
        """
        :param pos: 列表的文字对齐方式, left, right, middle三种方式
        :type pos: str
        :rtype: str
        """
        column = self.column
        column_title = self._add_split_sign(column)
        sign = [':------:']
        if pos == 'left':
            sign = [':------']
        elif pos == 'right':
            sign = ['------:']
        align_row = self._add_split_sign(len(column) * sign)
        return u"{column_title}\n{align_row}".format(
            column_title=column_title, align_row=align_row
        )

    def _generate_row(self):
        if len(self.data) > len(self.row):
            self.data = self.data[:len(self.row)]
        rows = []
        for index, row_data in enumerate(self.data):
            row = self.row[index] + map(str, row_data)
            rows.append(self._add_split_sign(row))
        return "\n".join(rows)

    def draw(self, pos=None):
        """
        :param pos: 列表的文字对齐方式, left, right, middle三种方式
        :type pos: str
        :rtype: str
        """
        title = self._generate_title(pos)
        content = self._generate_row()
        return u"{title}\n{content}".format(
            title=title, content=content
        )


class BaseObject(object):
    def setup_dict(self, data_dict, set_all=False):
        for k, v in data_dict.items():
            if (not set_all and k in self.__dict__) or set_all or k == 'name':
                setattr(self, k, v)

    @classmethod
    def setup_dict_list(cls, data_list):
        # type: (list[dict]) -> list[BaseObject]
        result = []
        for data in data_list:
            model = cls(**data)
            result.append(model)
        return result

    def to_dict(self):
        result_dict = {}
        for k, v in self.__dict__.items():
            if isinstance(v, list):
                if v:
                    if isinstance(v[0], BaseObject):
                        result_dict[k] = v[0].__class__.to_dict_list(*v)
                    else:
                        result_dict[k] = v
                else:
                    result_dict[k] = []
            elif type(v) in (float, int, list, dict, None, tuple, str, str, bool, int) or v is None:
                result_dict[k] = v
            elif type(v) == datetime:
                result_dict[k] = DateUtil.datetime_to_str(v)
            elif isinstance(v, ObjectDict):
                result_dict[k] = v
            else:
                dict_v = v.to_dict()
                result_dict[k] = dict_v
        return result_dict

    @staticmethod
    def to_dict_list(*objs):
        return [obj.to_dict() for obj in objs]

    def to_json(self):
        return json.dumps(self.to_dict())
