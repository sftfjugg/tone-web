import os

from django.http import JsonResponse


def migrate(request):
    result = os.system('python manage.py migrate')
    return JsonResponse({
        'success': not bool(result)
    })


def init_data(request):
    from tone.models import BaseConfig
    from initial.main import initialize_all

    if BaseConfig.objects.count() > 0:
        return JsonResponse({
            'success': False,
            'msg': 'Data already exists in the database. '
                   'If you need to initialize data, perform this operation manually'
        })

    initialize_all()
    return JsonResponse({
        'success': True
    })


def create_superuser(request):
    from tone.models import User, RoleMember, Role

    username = request.GET.get('username')
    password = request.GET.get('password')
    if not username:
        return JsonResponse({
            'success': False,
            'msg': 'Missing username parameter'
        })

    if not password:
        return JsonResponse({
            'success': False,
            'msg': 'Missing password parameter'
        })

    user = User.objects.create_user(
        username,
        password=password,
        ** {
            'emp_id': str((User.objects.count() + 1)).zfill(6),
            'first_name': username,
            'last_name': username,
            'is_superuser': True
        }
    )
    RoleMember.objects.create(
        user_id=user.id,
        role_id=Role.objects.get(title='sys_admin').id
    )

    return JsonResponse({
        'success': True,
        'msg': f'User({username}) created'
    })


def sync_cases(request):
    from tone.services.sys.sync_suite_task_servers import parse_toneagent_result, \
        update_cases_to_db, sync_case_info_from_oss
    # success, data = sync_case_info_by_tone_command()
    success, data = sync_case_info_from_oss()
    if not success:
        return JsonResponse({
            'success': False,
            'msg': data
        })
    suite_type_map, suite_conf_list_map = parse_toneagent_result(data)
    update_cases_to_db(suite_type_map, suite_conf_list_map)
    return JsonResponse({
        'success': True,
        'data': data
    })
