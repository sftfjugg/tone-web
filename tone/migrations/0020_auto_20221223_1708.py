# Generated by Django 2.2 on 2022-12-23 17:08

from django.db import migrations, models
import django_extensions.db.fields.json

class Migration(migrations.Migration):

    dependencies = [
        ('tone', '0019_auto_20221205_1145'),
    ]

    operations = [
        migrations.AddField(
            model_name='kernelinfo',
            name='kernel_packages',
            field=django_extensions.db.fields.json.JSONField(default={}, help_text='扩展包'),
        ),
    ]