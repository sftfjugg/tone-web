# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author:
"""

from rest_framework import serializers

from tone.core.common.serializers import CommonSerializer
from tone.models import User, TestCase, Project, TestSuite, TestMetric, CompareForm
from tone.models.report.test_report import ReportTemplate, ReportTmplItem, ReportTmplItemSuite, Report, ReportItem, \
    ReportItemMetric, ReportItemSubCase, ReportItemConf, ReportItemSuite


class ReportTemplateSerializer(CommonSerializer):
    creator_name = serializers.SerializerMethodField()
    update_user_name = serializers.SerializerMethodField()

    class Meta:
        model = ReportTemplate
        fields = ['id', 'name', 'creator', 'creator_name', 'update_user', 'update_user_name', 'description',
                  'gmt_created', 'gmt_modified', 'is_default']

    @staticmethod
    def get_creator_name(obj):
        creator_name = '系统预设'
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    @staticmethod
    def get_update_user_name(obj):
        update_user_name = None
        update_user = User.objects.filter(id=obj.update_user).first()
        if update_user:
            update_user_name = update_user.first_name if update_user.first_name else update_user.last_name
        return update_user_name


class ReportTemplateDetailSerializer(CommonSerializer):
    func_item = serializers.SerializerMethodField()
    perf_item = serializers.SerializerMethodField()
    perf_conf = serializers.SerializerMethodField()
    func_conf = serializers.SerializerMethodField()

    class Meta:
        model = ReportTemplate
        exclude = ['is_deleted']

    def get_func_conf(self, obj):
        return self.get_conf(obj.id, test_type='functional')

    def get_perf_conf(self, obj):
        return self.get_conf(obj.id, test_type='performance')

    @staticmethod
    def get_conf(tmpl_id, test_type):
        item_id_list = ReportTmplItem.objects.filter(tmpl_id=tmpl_id, test_type=test_type).values_list('id')
        item_suite = ReportTmplItemSuite.objects.filter(report_tmpl_item_id__in=item_id_list).first()
        if item_suite is not None:
            res = {
                'need_test_description': item_suite.need_test_description,
                'test_description_desc': item_suite.test_description_desc,
                'need_test_conclusion': item_suite.need_test_conclusion,
                'test_conclusion_desc': item_suite.test_conclusion_desc,
            }
            if test_type == 'performance':
                res.update({
                    'need_test_suite_description': item_suite.need_test_suite_description,
                    'show_type': item_suite.show_type,
                    'need_test_env': item_suite.need_test_env,
                    'test_env_desc': item_suite.test_env_desc
                })
            return res

    def get_func_item(self, obj):
        if obj.is_default:
            return [
                {
                    "name": "测试项1",
                    "list": [
                        {
                            "test_tool": None,
                            "suite_show_name": "TestSuite",
                            "case_source": [
                                {
                                    "test_conf_name": "TestConf"
                                },
                                {
                                    "test_conf_name": "TestConf"
                                },
                                {
                                    "test_conf_name": "TestConf"
                                },
                            ]
                        }]
                },
                {
                    "name": "测试项2",
                    "list": [
                        {
                            "test_tool": None,
                            "suite_show_name": "TestSuite",
                            "case_source": [
                                {
                                    "test_conf_name": "TestConf"
                                },
                                {
                                    "test_conf_name": "TestConf"
                                },
                                {
                                    "test_conf_name": "TestConf"
                                },
                            ]
                        },
                        {
                            "test_tool": None,
                            "suite_show_name": "TestSuite",
                            "case_source": [
                                {
                                    "test_conf_name": "TestConf"
                                },
                                {
                                    "test_conf_name": "TestConf"
                                },
                                {
                                    "test_conf_name": "TestConf"
                                },
                            ]
                        }
                    ]
                }
            ]
        return self.get_item_data_list(obj.id, test_type='functional')

    def get_perf_item(self, obj):
        if obj.is_default:
            return [
                {
                    "name": "测试项1",
                    "list": [
                        {
                            "test_tool": None,
                            "suite_show_name": "TestSuite",
                            "case_source": [
                                {
                                    "test_conf_name": "TestConf",
                                    "metric_list": ["Metric", "Metric", "Metric"]
                                },
                                {
                                    "test_conf_name": "TestConf",
                                    "metric_list": ["Metric", "Metric", "Metric"]
                                }
                            ]
                        }
                    ]
                }
            ]
        return self.get_item_data_list(obj.id, test_type='performance')

    def pack_group_name(self, item_name_list, pack_data):
        if len(item_name_list) > 1:
            if 'group_data' in pack_data:
                pack_data['group_data'] = {'group_name': item_name_list[0],
                                           'group_data': None}

            else:
                pack_data = {'group_name': item_name_list[0],
                             'group_data': {}}
            return self.pack_group_name(item_name_list[1:], pack_data)
        else:

            if 'group_data' in pack_data:
                pack_data['group_data'] = {'group_name': item_name_list[0],
                                           'group_data': {'item_name': item_name_list[0],
                                                          'test_suite_list': []}}
            else:
                pack_data = {'name': item_name_list[0],
                             'test_suite_list': []}
            return pack_data

    @staticmethod
    def trans_data(group_name_map):
        result = list()
        parent_dic = {}
        for group_name in group_name_map.keys():
            # 多级分组, 目前支持到三级
            if ':' in group_name:
                parent_name = group_name.split(':')[0]
                son_name = ':'.join(group_name.split(':')[1:])
                if parent_name in parent_dic:
                    parent_dic[parent_name].append({
                        son_name: group_name_map[group_name]
                    })
                else:
                    parent_dic[parent_name] = [{
                        son_name: group_name_map[group_name]
                    }]
            else:
                result.append({
                    'name': group_name,
                    'is_group': True,
                    'list': group_name_map[group_name]
                })

        for tmp in parent_dic:
            tmp_dict = {'name': tmp,
                        'is_group': True,
                        'list': []}
            son_list = parent_dic[tmp]
            for son_tmp in son_list:
                son_name = list(son_tmp.keys())[0]
                tmp_dict['list'].append({
                    'name': son_name,
                    'is_group': True,
                    'list': son_tmp[son_name]
                })
            result.append(tmp_dict)
        return result

    def init_list(self, son_list, new_list):
        for son in son_list:
            if son.son_list:
                new_list.append({
                    'name': son.name,
                    'is_group': True,
                    'list': self.init_list(son.son_list, [])
                })
            else:
                new_list.append({
                    'name': son.name,
                    'list': son.item
                })
        return new_list

    def pack_item_data(self, item_data_map):
        class Node:
            def __init__(self, name, item):
                self.son_list = list()
                self.name = name
                self.item = item

            def add_son(self, son):
                self.son_list.append(son)

        def pack_root(origin_data, parent):
            next_name = list()
            for tmp_data in origin_data:
                if ':' in tmp_data:
                    first = tmp_data.split(':')[0]
                    next_name.append(first)

            next_data = {name: {} for name in next_name}
            for key_name, key_value in origin_data.items():
                if ':' in key_name:
                    first, res = key_name.split(':')[0], key_name.split(':')[1:]
                    next_data[first][':'.join(res)] = key_value
                else:
                    son = Node(key_name, key_value)
                    parent.add_son(son)
            for tmp_name in next_data:
                son = Node(tmp_name, next_data[tmp_name])
                parent.add_son(son)
                pack_root(next_data[tmp_name], son)

        root = Node('root', None)
        pack_root(item_data_map, root)
        result = list()
        return self.init_list(root.son_list, result)

    def get_item_data_list(self, tmpl_id, test_type):
        item_data_list = list()
        group_name_map = dict()
        result = list()
        item_data_map = dict()
        for tmp_item in sorted(ReportTmplItem.objects.filter(tmpl_id=tmpl_id, test_type=test_type),
                               key=lambda item: item.name):

            item_suite_list = list()
            for item_suite in ReportTmplItemSuite.objects.filter(report_tmpl_item_id=tmp_item.id):
                case_source = [{'test_conf_id': case_id, 'test_conf_name': case_name,
                                'metric_list': TestMetric.objects.filter(
                                    object_type='case', object_id=case_id).values_list('name', flat=True)
                                } for case_id, case_name in
                               TestCase.objects.filter(id__in=item_suite.test_conf_list).values_list('id', 'name')]
                tmp_suite = TestSuite.objects.filter(id=item_suite.test_suite_id).first()
                item_suite_data = {
                    'test_suite_id': item_suite.test_suite_id,
                    'test_tool': None if not tmp_suite else tmp_suite.doc,
                    'suite_show_name': item_suite.test_suite_show_name,
                    'case_source': case_source,
                }
                item_suite_list.append(item_suite_data)
            item_data_list.append({
                'name': tmp_item.name,
                'test_suite_list': item_suite_list
            })
            item_data_map[tmp_item.name] = item_suite_list

            if ':' in tmp_item.name:
                item_name = tmp_item.name.split(':')[-1]
                group_names = ':'.join(tmp_item.name.split(':')[:-1])
                item_data = {
                    'name': item_name,
                    'list': item_suite_list
                }
                if group_names not in group_name_map:
                    group_name_map[group_names] = [item_data]
                else:
                    group_name_map[group_names].append(item_data)
            else:
                result.append({
                    'name': tmp_item.name,
                    'list': item_suite_list
                })
        return self.pack_item_data(item_data_map)


class ReportSerializer(CommonSerializer):
    creator = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    creator_id = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ['id', 'name', 'description', 'creator', 'product_version', 'project', 'gmt_modified', 'creator_id']

    @staticmethod
    def get_creator_id(obj):
        return obj.creator

    @staticmethod
    def get_creator(obj):
        user = User.objects.get(id=obj.creator)
        creator = user.first_name if user.first_name else user.last_name
        return creator

    @staticmethod
    def get_project(obj):
        if Project.objects.filter(id=obj.project_id).exists():
            project = Project.objects.get_value(id=obj.project_id)
            return project.name
        return ''


class ReportDetailSerializer(CommonSerializer):
    test_item = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    group_count = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ['id', 'name', 'test_background', 'test_conclusion', 'test_method', 'test_env', 'report_source',
                  'description', 'test_item', 'tmpl_id', 'gmt_created', 'creator', 'creator_name',
                  'env_description', 'group_count']

    @staticmethod
    def get_creator_name(obj):
        creator_name = None
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    def get_test_item(self, obj):
        perf_data = self.get_perf_data(obj.id)
        func_data = self.get_func_data(obj.id)
        return {'perf_data': perf_data, 'func_data': func_data}

    @staticmethod
    def get_perf_data(report_id):
        item_map = dict()
        item_objs = ReportItem.objects.filter(report_id=report_id, test_type='performance')
        for item in item_objs:
            name = item.name
            name_li = name.split(':')
            package_name(0, item_map, name_li, item.id, 'performance')
        return item_map

    @staticmethod
    def get_func_data(report_id):
        item_map = dict()
        item_objs = ReportItem.objects.filter(report_id=report_id, test_type='functional')
        for item in item_objs:
            name = item.name
            name_li = name.split(':')
            package_name(0, item_map, name_li, item.id, 'functional')
        return item_map

    @staticmethod
    def get_group_count(obj):
        group_count = 1
        if 'summary' in obj.test_conclusion and 'compare_groups' in obj.test_conclusion['summary']:
            group_count = len(obj.test_conclusion['summary']['compare_groups']) + 1
        return group_count


def package_name(index, _data, name_li, report_item_id, test_type):
    if index == len(name_li) - 1:
        _data[name_li[index]] = get_func_suite_list(
            report_item_id) if test_type == 'functional' else get_perf_suite_list(report_item_id)
    else:
        if name_li[index] in _data:
            package_name(index + 1, _data[name_li[index]], name_li, report_item_id, test_type)
        else:
            _data[name_li[index]] = dict()
            package_name(index + 1, _data[name_li[index]], name_li, report_item_id, test_type)


def get_func_suite_list(report_item_id):
    suite_list = list()
    test_suite_objs = ReportItemSuite.objects.filter(report_item_id=report_item_id)
    for test_suite_obj in test_suite_objs:
        suite_data = dict()
        suite_data['item_suite_id'] = test_suite_obj.id
        suite_data['suite_id'] = test_suite_obj.test_suite_id
        suite_data['suite_name'] = test_suite_obj.test_suite_name
        conf_list = list()
        test_conf_objs = ReportItemConf.objects.filter(report_item_suite_id=test_suite_obj.id)
        for test_conf_obj in test_conf_objs:
            conf_data = dict()
            conf_data['item_conf_id'] = test_conf_obj.id
            conf_data['conf_id'] = test_conf_obj.test_conf_id
            conf_data['conf_name'] = test_conf_obj.test_conf_name
            conf_data['conf_source'] = test_conf_obj.conf_source
            conf_data['compare_conf_list'] = test_conf_obj.compare_conf_list
            sub_case_list = list()
            sub_case_objs = ReportItemSubCase.objects.filter(report_item_conf_id=test_conf_obj.id)
            for sub_case_obj in sub_case_objs:
                sub_case_data = dict()
                sub_case_data['sub_case_name'] = sub_case_obj.sub_case_name
                sub_case_data['result'] = sub_case_obj.result
                sub_case_data['compare_data'] = sub_case_obj.compare_data
                sub_case_list.append(sub_case_data)
            conf_data['sub_case_list'] = sub_case_list
            conf_list.append(conf_data)
        suite_data['conf_list'] = conf_list
        suite_list.append(suite_data)
    return suite_list


def _get_compare_data(metric_obj):
    compare_data = list()
    for item in metric_obj.compare_data:
        if item:
            item['compare_value'] = item['compare_value'].strip('-') if item.get('compare_value') else ''
            compare_data.append(item)
    return compare_data


def get_perf_suite_list(report_item_id):
    suite_list = list()
    test_suite_objs = ReportItemSuite.objects.filter(report_item_id=report_item_id)
    for test_suite_obj in test_suite_objs:
        suite_data = dict()
        suite_data['item_suite_id'] = test_suite_obj.id
        suite_data['suite_name'] = test_suite_obj.test_suite_name
        suite_data['suite_id'] = test_suite_obj.test_suite_id
        suite_data['show_type'] = test_suite_obj.show_type
        suite_data['test_suite_description'] = ''
        test_suite = TestSuite.objects.filter(name=test_suite_obj.test_suite_name).first()
        if test_suite:
            suite_data['test_suite_description'] = test_suite.doc
        suite_data['test_env'] = test_suite_obj.test_env
        suite_data['test_description'] = test_suite_obj.test_description
        suite_data['test_conclusion'] = test_suite_obj.test_conclusion
        conf_list = list()
        test_conf_objs = ReportItemConf.objects.filter(report_item_suite_id=test_suite_obj.id)
        for test_conf_obj in test_conf_objs:
            conf_data = dict()
            conf_data['item_conf_id'] = test_conf_obj.id
            conf_data['conf_id'] = test_conf_obj.test_conf_id
            conf_data['conf_name'] = test_conf_obj.test_conf_name
            conf_data['conf_source'] = test_conf_obj.conf_source
            conf_data['compare_conf_list'] = test_conf_obj.compare_conf_list
            metric_list = list()
            metric_objs = ReportItemMetric.objects.filter(report_item_conf_id=test_conf_obj.id)
            for metric_obj in metric_objs:
                test_metric = TestMetric.objects.filter(name=metric_obj.test_metric, object_type='case').first()
                compare_data = _get_compare_data(metric_obj)
                metric_data = dict()
                metric_data['metric'] = metric_obj.test_metric
                metric_data['test_value'] = format(float(metric_obj.test_value), '.2f') \
                    if metric_obj.test_value else ''
                metric_data['cv_value'] = metric_obj.cv_value
                metric_data['unit'] = metric_obj.unit
                metric_data['max_value'] = metric_obj.max_value
                metric_data['min_value'] = metric_obj.min_value
                metric_data['value_list'] = metric_obj.value_list
                metric_data['direction'] = metric_obj.direction
                metric_data['cv_threshold'] = test_metric.cv_threshold if test_metric else None
                metric_data['cmp_threshold'] = test_metric.cmp_threshold if test_metric else None
                metric_data['compare_data'] = compare_data
                metric_list.append(metric_data)
            conf_data['metric_list'] = metric_list
            conf_list.append(conf_data)
        suite_data['conf_list'] = conf_list
        suite_list.append(suite_data)
    return suite_list


class CompareFormSerializer(CommonSerializer):

    class Meta:
        model = CompareForm
        fields = ['req_form']
