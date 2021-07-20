# Generated by Django 3.2.1 on 2021-07-14 12:22

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("institutions", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("invitations", "0005_remove_duplicates"),
    ]

    operations = [
        migrations.CreateModel(
            name="LaborInspectorInvitation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(max_length=254, verbose_name="E-mail")),
                ("first_name", models.CharField(max_length=255, verbose_name="Prénom")),
                ("last_name", models.CharField(max_length=255, verbose_name="Nom")),
                ("sent", models.BooleanField(default=False, verbose_name="Envoyée")),
                ("accepted", models.BooleanField(default=False, verbose_name="Acceptée")),
                (
                    "accepted_at",
                    models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="Date d'acceptation"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        db_index=True, default=django.utils.timezone.now, verbose_name="Date de création"
                    ),
                ),
                ("sent_at", models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="Date d'envoi")),
                (
                    "institution",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="labor_inspectors_invitations",
                        to="institutions.institution",
                    ),
                ),
                (
                    "sender",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="institution_invitations",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Parrain ou marraine",
                    ),
                ),
            ],
            options={
                "verbose_name": "Invitation inspecteurs du travail",
                "verbose_name_plural": "Invitations inspecteurs du travail",
            },
        ),
    ]
