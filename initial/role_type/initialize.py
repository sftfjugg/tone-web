from initial.role_type.data import ROLE_TYPE_ITEM_DATA
from tone.models import Role


class RoleTypeDataInitialize(object):

    def initialize_role_type_item(self):
        self._clear_role_type_item_data()
        self._add_role_type_item_data()

    @staticmethod
    def _clear_role_type_item_data():
        Role.objects.all(query_scope='all').delete(really_delete=True)

    @staticmethod
    def _add_role_type_item_data():
        role_type_obj_list = [
            Role(
                title=role_type_item['title'],
                description=role_type_item['description'],
                role_type=role_type_item['role_type'],
            )
            for role_type_item in ROLE_TYPE_ITEM_DATA
        ]
        Role.objects.bulk_create(role_type_obj_list)
