# Generated by Django 3.2.1 on 2021-07-29 14:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("prescribers", "0031_prescriberorganization_is_head_office"),
    ]

    operations = [
        migrations.AlterField(
            model_name="prescribermembership",
            name="is_admin",
            field=models.BooleanField(default=False, verbose_name="Administrateur"),
        ),
    ]
