# Generated by Django 3.2.7 on 2021-09-20 14:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("job_applications", "0037_alter_jobapplication_refusal_reason"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobapplication",
            name="answer_to_prescriber",
            field=models.TextField(blank=True, verbose_name="Message de réponse au prescripeur"),
        ),
    ]
