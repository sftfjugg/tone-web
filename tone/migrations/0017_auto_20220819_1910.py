# Generated by Django 3.2.5 on 2022-08-19 19:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tone', '0016_auto_20220817_1931'),
    ]

    operations = [
        migrations.AddField(
            model_name='cloudserversnapshot',
            name='cpu_info',
            field=models.TextField(help_text='CPU信息', null=True),
        ),
        migrations.AddField(
            model_name='cloudserversnapshot',
            name='disk',
            field=models.TextField(help_text='磁盘信息', null=True),
        ),
        migrations.AddField(
            model_name='cloudserversnapshot',
            name='ether',
            field=models.TextField(help_text='网卡信息', null=True),
        ),
        migrations.AddField(
            model_name='cloudserversnapshot',
            name='glibc',
            field=models.TextField(help_text='glibc信息', null=True),
        ),
        migrations.AddField(
            model_name='cloudserversnapshot',
            name='memory_info',
            field=models.TextField(help_text='内存信息', null=True),
        ),
        migrations.AddField(
            model_name='testserversnapshot',
            name='cpu_info',
            field=models.TextField(help_text='CPU信息', null=True),
        ),
        migrations.AddField(
            model_name='testserversnapshot',
            name='disk',
            field=models.TextField(help_text='磁盘信息', null=True),
        ),
        migrations.AddField(
            model_name='testserversnapshot',
            name='ether',
            field=models.TextField(help_text='网卡信息', null=True),
        ),
        migrations.AddField(
            model_name='testserversnapshot',
            name='glibc',
            field=models.TextField(help_text='glibc信息', null=True),
        ),
        migrations.AddField(
            model_name='testserversnapshot',
            name='memory_info',
            field=models.TextField(help_text='内存信息', null=True),
        ),
    ]