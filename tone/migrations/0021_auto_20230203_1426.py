# Generated by Django 3.2.5 on 2023-02-03 14:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tone', '0020_auto_20221223_1708'),
    ]

    operations = [
        migrations.CreateModel(
            name='JobDownloadRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gmt_created', models.DateTimeField(auto_now_add=True, help_text='创建时间', verbose_name='create_at')),
                ('gmt_modified', models.DateTimeField(auto_now=True, help_text='修改时间', verbose_name='modify_at')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否被删除')),
                ('job_id', models.IntegerField(db_index=True, help_text='job id')),
                ('state', models.CharField(choices=[('running', '文件打包中'), ('success', '成功'), ('fail', '失败')], default='running', help_text='state', max_length=64)),
                ('job_url', models.CharField(help_text='job下载链接', max_length=256, null=True)),
            ],
            options={
                'db_table': 'job_download_record',
            },
        ),
    ]