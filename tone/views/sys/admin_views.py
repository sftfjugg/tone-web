import os

from django.http import JsonResponse

from initial.main import initialize_all
from tone.models import User, RoleMember, Role, BaseConfig


def migrate(request):
    result = os.system('python manage.py migrate')
    return JsonResponse({
        'success': bool(result)
    })


def init_data(request):
    if BaseConfig.objects.count() > 0:
        return JsonResponse({
            'success': False,
            'msg': '数据库中已有数据，如需初始化请手动操作'
        })

    initialize_all()
    return JsonResponse({
        'success': True
    })


def create_superuser(request):
    username = request.GET.get('username')
    if not username:
        return JsonResponse({
            'success': False,
            'msg': '缺少 username 参数'
        })

    user = User.objects.create_user(
        username,
        **{
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
        'msg': f'{username} 创建成功'
    })
