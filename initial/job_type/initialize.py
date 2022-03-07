from initial.job_type.data import JOB_TYPE_ITEM_DATA, JOB_TYPE_TMPL_DATA
from tone.models import JobType, JobTypeItem, JobTypeItemRelation, Workspace


class JobTypeDataInitialize(object):

    def initialize_job_type_item(self):
        self._clear_job_type_item_data()
        self._add_job_type_item_data()
        for ws in Workspace.objects.all():
            self.initialize_ws_job_type(ws.id)

    def initialize_ws_job_type(self, ws_id):
        self.clear_ws_job_type_data(ws_id=ws_id)
        self._add_ws_job_type_data(ws_id=ws_id)

    @staticmethod
    def _clear_job_type_item_data():
        JobTypeItem.objects.all(query_scope='all').delete(really_delete=True)

    @staticmethod
    def _clear_job_type_tmpl_data():
        JobType.objects.filter(query_scope='all').delete(really_delete=True)

    @staticmethod
    def clear_ws_job_type_data(ws_id):
        job_type_list = JobType.objects.filter(ws_id=ws_id, query_scope='all').values_list('id', flat=True)
        JobTypeItemRelation.objects.filter(job_type_id__in=job_type_list, query_scope='all').delete(really_delete=True)
        JobType.objects.filter(id__in=list(job_type_list), query_scope='all').delete(really_delete=True)

    @staticmethod
    def _add_job_type_item_data():
        job_type_obj_list = [
            JobTypeItem(
                name=job_type_item['name'],
                show_name=job_type_item['show_name'],
                description=job_type_item['description'],
                config_index=job_type_item['config_index']
            )
            for job_type_item in JOB_TYPE_ITEM_DATA
        ]
        JobTypeItem.objects.bulk_create(job_type_obj_list)

    @staticmethod
    def _add_ws_job_type_data(ws_id):
        for item in JOB_TYPE_TMPL_DATA:
            job_type_item_relation_obj_list = []
            job_type = JobType.objects.create(
                name=item['name'],
                test_type=item['test_type'],
                server_type=item['server_type'],
                description=item['description'],
                priority=item['priority'],
                is_default=item.get('is_default', False),
                is_first=item.get('is_first', False),
                enable=item.get('enable', False),
                ws_id=ws_id,
                creator=0
            )
            for relation_item in item['items']:
                job_type_item = JobTypeItem.objects.get(name=relation_item[0], config_index=relation_item[1])
                job_type_item_relation_obj_list.append(
                    JobTypeItemRelation(
                        job_type_id=job_type.id,
                        item_id=job_type_item.id,
                        item_show_name=job_type_item.show_name
                    )
                )
            JobTypeItemRelation.objects.bulk_create(job_type_item_relation_obj_list)
