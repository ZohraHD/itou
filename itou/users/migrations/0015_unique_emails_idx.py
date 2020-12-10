# Generated by Django 3.1.3 on 2020-12-09 11:05

import django.contrib.postgres.fields.citext
from django.contrib.auth import get_user_model
from django.db import migrations


def move_data_forward(apps, schema_editor):
    """
    Replace old `blank` by `null` values.
    """
    get_user_model().objects.filter(email="").update(email=None)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0014_auto_20201007_1736"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="email",
            field=django.contrib.postgres.fields.citext.CIEmailField(
                blank=True, db_index=True, max_length=254, null=True, unique=True, verbose_name="email address"
            ),
        ),
        # Replace old `blank` by `null` values.
        migrations.RunPython(move_data_forward, migrations.RunPython.noop),
    ]
