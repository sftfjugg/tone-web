# Generated by Django 3.2.5 on 2023-02-24 10:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tone', '0022_merge_0021_auto_20230106_1603_0021_auto_20230203_1426'),
    ]

    operations = [
        migrations.CreateModel(
            name='BaselineServerSnapshot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gmt_created', models.DateTimeField(auto_now_add=True, help_text='创建时间', verbose_name='create_at')),
                ('gmt_modified', models.DateTimeField(auto_now=True, help_text='修改时间', verbose_name='modify_at')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否被删除')),
                ('baseline_id', models.IntegerField(blank=True, db_index=True, help_text='基线Id', null=True)),
                ('test_job_id', models.IntegerField(db_index=True, help_text='关联JOB ID')),
                ('test_suite_id', models.IntegerField(db_index=True, help_text='关联SUITE ID')),
                ('test_case_id', models.IntegerField(db_index=True, help_text='关联CASE ID')),
                ('ip', models.CharField(blank=True, db_index=True, help_text='IP', max_length=64, null=True)),
                ('sn', models.CharField(blank=True, help_text='SN', max_length=64, null=True)),
                ('image', models.CharField(blank=True, help_text='镜像', max_length=64, null=True)),
                ('bandwidth', models.IntegerField(blank=True, help_text='最大带宽', null=True)),
                ('sm_name', models.CharField(blank=True, help_text='机型', max_length=64, null=True)),
                ('kernel_version', models.CharField(blank=True, help_text='内核版本', max_length=64, null=True)),
                ('distro', models.CharField(help_text='发行版本', max_length=256, null=True)),
                ('gcc', models.TextField(help_text='gcc版本', null=True)),
                ('rpm_list', models.TextField(help_text='rpm包', null=True)),
                ('glibc', models.TextField(help_text='glibc信息', null=True)),
                ('memory_info', models.TextField(help_text='内存信息', null=True)),
                ('disk', models.TextField(help_text='磁盘信息', null=True)),
                ('cpu_info', models.TextField(help_text='CPU信息', null=True)),
                ('ether', models.TextField(help_text='网卡信息', null=True)),
            ],
            options={
                'db_table': 'baseline_server_snapshot',
            },
        ),
    ]
