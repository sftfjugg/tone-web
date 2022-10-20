# Generated by Django 3.2.5 on 2022-10-20 10:05

from django.db import migrations, models
import django_extensions.db.fields.json


class Migration(migrations.Migration):

    dependencies = [
        ('tone', '0017_auto_20220819_1910'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReportDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gmt_created', models.DateTimeField(auto_now_add=True, help_text='创建时间', verbose_name='create_at')),
                ('gmt_modified', models.DateTimeField(auto_now=True, help_text='修改时间', verbose_name='modify_at')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否被删除')),
                ('report_id', models.IntegerField(help_text='关联报告ID')),
                ('perf_data', models.JSONField()),
                ('func_data', models.JSONField()),
            ],
            options={
                'db_table': 'report_detail',
            },
        ),
        migrations.AddField(
            model_name='planinstance',
            name='report_is_saved',
            field=models.BooleanField(default=False, help_text='是否已保存报告'),
        ),
        migrations.AddField(
            model_name='planinstance',
            name='script_info',
            field=django_extensions.db.fields.json.JSONField(default=[], help_text='脚本信息'),
        ),
        migrations.AddField(
            model_name='testplan',
            name='script_info',
            field=django_extensions.db.fields.json.JSONField(default=[], help_text='脚本信息'),
        ),
    ]
