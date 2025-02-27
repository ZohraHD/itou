# Generated by Django 3.1.3 on 2020-12-01 11:36

import django.contrib.postgres.constraints
import django.contrib.postgres.fields.ranges
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import itou.utils.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("users", "0001bis_create_extensions"),
        ("siaes", "0041_auto_20201120_1421"),
        ("approvals", "0009_auto_20200222_1128"),
    ]

    operations = [
        migrations.CreateModel(
            name="Suspension",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "start_at",
                    models.DateField(db_index=True, default=django.utils.timezone.now, verbose_name="Date de début"),
                ),
                (
                    "end_at",
                    models.DateField(db_index=True, default=django.utils.timezone.now, verbose_name="Date de fin"),
                ),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("SICKNESS", "Arrêt pour longue maladie"),
                            ("MATERNITY", "Congé de maternité"),
                            ("INCARCERATION", "Incarcération"),
                            (
                                "TRIAL_OUTSIDE_IAE",
                                "Période d'essai auprès d'un employeur ne relevant pas de l'insertion par "
                                "l'activité économique",
                            ),
                            ("DETOXIFICATION", "Période de cure pour désintoxication"),
                            (
                                "FORCE_MAJEURE",
                                "Raison de force majeure conduisant le salarié à quitter son emploi ou toute "
                                "autre situation faisant l'objet d'un accord entre les acteurs membres du CTA",
                            ),
                        ],
                        default="SICKNESS",
                        max_length=30,
                        verbose_name="Motif",
                    ),
                ),
                ("reason_explanation", models.TextField(blank=True, verbose_name="Explications supplémentaires")),
                (
                    "created_at",
                    models.DateTimeField(default=django.utils.timezone.now, verbose_name="Date de création"),
                ),
                ("updated_at", models.DateTimeField(blank=True, null=True, verbose_name="Date de modification")),
                (
                    "approval",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="approvals.approval", verbose_name="PASS IAE"
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="approvals_suspended_set",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Créé par",
                    ),
                ),
                (
                    "siae",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="approvals_suspended",
                        to="siaes.siae",
                        verbose_name="SIAE",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Mis à jour par",
                    ),
                ),
            ],
            options={"verbose_name": "Suspension", "verbose_name_plural": "Suspensions", "ordering": ["-start_at"]},
        ),
        migrations.AddConstraint(
            model_name="suspension",
            constraint=django.contrib.postgres.constraints.ExclusionConstraint(
                expressions=(
                    (
                        itou.utils.models.DateRange(
                            "start_at",
                            "end_at",
                            django.contrib.postgres.fields.ranges.RangeBoundary(
                                inclusive_lower=True, inclusive_upper=True
                            ),
                        ),
                        "&&",
                    ),
                    ("approval", "="),
                ),
                name="exclude_overlapping_suspensions",
            ),
        ),
    ]
