# Generated by Django 3.2.4 on 2021-06-19 15:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("asp", "0005_alter_country_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="commune",
            name="code",
            field=models.CharField(db_index=True, max_length=5, verbose_name="Code commune INSEE"),
        ),
    ]
