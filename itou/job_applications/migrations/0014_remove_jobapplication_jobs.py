# Generated by Django 2.2.6 on 2019-11-11 18:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("job_applications", "0013_copy_data")]

    operations = [migrations.RemoveField(model_name="jobapplication", name="jobs")]
