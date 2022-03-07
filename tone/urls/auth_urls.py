from django.urls import path

from tone.views.auth import auth_views

urlpatterns = [
    # auth
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', auth_views.RegisterView.as_view(), name='register'),
    path('reset_password/', auth_views.ResetPasswordView.as_view(), name='reset_password'),
    path('change_password/', auth_views.ChangePasswordView.as_view(), name='change_password'),
    path('user/', auth_views.UserView.as_view(), name='user'),
    path('user/', auth_views.UserView.as_view(), name='user'),
    path('user/detail/', auth_views.UserDetailView.as_view(), name='user_detail'),
    path('role/', auth_views.RoleView.as_view(), name='role'),
    path('personal_workspace/', auth_views.PersonalWorkspaceView.as_view(), name='personal_workspace'),
    path('personal_approve/', auth_views.PersonalApproveView.as_view(), name='personal_approve'),
    path('personal_token/', auth_views.PersonalTokenView.as_view(), name='personal_token'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('personal_center/', auth_views.PersonalCenterView.as_view(), name='personal_center'),
    path('re_login/', auth_views.ReLoginView.as_view(), name='re_login'),
    path('re_apply/', auth_views.ReApplyView.as_view(), name='re_apply'),
    path('ws_admin/', auth_views.FilterWsAdminView.as_view(), name='ws_tester_admin'),
    path('msg_state/', auth_views.MsgStateView.as_view(), name='msg_state'),
    path('task_msg/', auth_views.TaskMsgView.as_view(), name='task_msg'),
    path('apply_msg/', auth_views.ApplyMsgView.as_view(), name='apply_msg'),
]
