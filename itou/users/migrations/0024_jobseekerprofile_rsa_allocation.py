# Generated by Django 3.1.7 on 2021-04-06 16:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0023_auto_20210322_1826"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobseekerprofile",
            name="has_rsa_allocation",
            field=models.CharField(
                choices=[
                    ("OUI-M", "Bénéficiaire du RSA et majoré"),
                    ("OUI-NM", "Bénéficiaire du RSA et non-majoré"),
                    ("NON", "Non bénéficiaire du RSA"),
                ],
                default="NON",
                max_length=6,
                verbose_name="Salarié bénéficiaire du RSA",
            ),
        ),
    ]
