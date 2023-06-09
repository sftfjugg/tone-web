from django.db import transaction

from tone.core.utils.short_uuid import short_uuid
from tone.models import Workspace, User, RoleMember, Role
from tone.services.sys.workspace_services import WorkspaceService


class WorkspaceDataInitialize(object):

    def initialize_common_ws(self):
        with transaction.atomic():
            system_user = User.objects.filter(username='system', is_superuser=True).first()
            if not system_user:
                system_user = User.objects.create_user(
                    'system',
                    **{'emp_id': '000000', 'first_name': 'admin', 'last_name': 'tone', 'is_superuser': True}
                )
                RoleMember.objects.create(
                    user_id=system_user.id,
                    role_id=Role.objects.get(title='sys_admin').id
                )
            ws_id = short_uuid()
            Workspace.objects.create(
                id=ws_id,
                name='common_workspace',
                show_name='公共workspace',
                is_common=True,
                is_public=True,
                is_approved=True,
                theme_color='#5B8FF9',
                owner=system_user.id,
                creator=system_user.id
            )

            WorkspaceService().add_workspace_relation_data(ws_id, system_user.id, first_init=True)
