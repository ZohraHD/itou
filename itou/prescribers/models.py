from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.contrib.postgres.search import TrigramSimilarity
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from itou.utils.address.models import AddressMixin
from itou.utils.emails import get_email_message
from itou.utils.validators import validate_code_safir, validate_siret


class PrescriberOrganizationQuerySet(models.QuerySet):
    def member_required(self, user):
        if user.is_superuser:
            return self
        return self.filter(members=user, members__is_active=True)

    def autocomplete(self, search_string, limit=10):
        queryset = (
            self.annotate(similarity=TrigramSimilarity("name", search_string))
            .filter(similarity__gt=0.1)
            .order_by("-similarity")
        )
        return queryset[:limit]

    def by_safir_code(self, safir_code):
        return self.filter(code_safir_pole_emploi=safir_code).first()

    def within(self, point, distance_km):
        return (
            self.filter(coords__distance_lte=(point, D(km=distance_km)))
            .annotate(distance=Distance("coords", point))
            .order_by("distance")
        )


class PrescriberOrganization(AddressMixin):  # Do not forget the mixin!
    """
    The organization of a prescriber, e.g.: Pôle emploi, missions locales, Cap emploi etc.

    A "prescriber" is always represented by a User object with the `is_prescriber` flag set to `True`.

    The "prescriber" has the possibility of being a member of an organisation represented by a
    `PrescriberOrganization` object through `PrescriberMembership`.

    However it is not required for a "prescriber" to be a member of an organization.

    There are 3 possible cases:

    Case 1
        A "prescriber" is alone (e.g. "éducateur de rue"). In this case there is only a `User` object
            - User.is_prescriber = True

    Case 2
        A "prescriber" is a member of an organization (e.g. an association of unemployed people etc.)
        and uses the platform with 0 or n collaborators.
        In this case there are 3 objects:
            - User.is_prescriber = True
            - PrescriberOrganization.is_authorized = False
            - PrescriberMembership

    Case 3
        This case is a variant of case 2 where the organization is "authorized" at national level or by
        the Prefect (e.g. Pôle emploi, CCAS, Cap emploi…). This is similar to case 2  with an additional
        flag for the organization:
            - User.is_prescriber = True
            - PrescriberOrganization.is_authorized = True
            - PrescriberMembership

    In the last 2 cases, there can be n members by organization.

    In case 1 and case 2, we talk about "orienteur" in French.

    In case 3, we talk about "prescripteur habilité" in French.
    """

    class Kind(models.TextChoices):
        PE = "PE", _("Pôle emploi")
        CAP_EMPLOI = "CAP_EMPLOI", _("CAP emploi")
        ML = "ML", _("Mission locale")
        DEPT = "DEPT", _("Service social du conseil départemental")
        DEPT_BRSA = "DEPT_BRSA", _("Dispositif conventionné par le conseil départemental pour le suivi BRSA")
        SPIP = "SPIP", _("SPIP - Service pénitentiaire d'insertion et de probation")
        PJJ = "PJJ", _("PJJ - Protection judiciaire de la jeunesse")
        CCAS = ("CCAS", _("CCAS - Centre communal d'action sociale ou centre intercommunal d'action sociale"))
        PLIE = "PLIE", _("PLIE - Plan local pour l'insertion et l'emploi")
        CHRS = "CHRS", _("CHRS - Centre d'hébergement et de réinsertion sociale")
        CIDFF = ("CIDFF", _("CIDFF - Centre d'information sur les droits des femmes et des familles"))
        PREVENTION = "PREVENTION", _("Service ou club de prévention")
        AFPA = ("AFPA", _("AFPA - Agence nationale pour la formation professionnelle des adultes"))
        PIJ_BIJ = "PIJ_BIJ", _("PIJ-BIJ - Point/Bureau information jeunesse")
        CAF = "CAF", _("CAF - Caisse d'allocation familiale")
        CADA = "CADA", _("CADA - Centre d'accueil de demandeurs d'asile")
        ASE = "ASE", _("ASE - Aide sociale à l'enfance")
        CAVA = "CAVA", _("CAVA - Centre d'adaptation à la vie active")
        CPH = "CPH", _("CPH - Centre provisoire d'hébergement")
        CHU = "CHU", _("CHU - Centre d'hébergement d'urgence")
        OACAS = (
            "OACAS",
            _(
                "OACAS - Structure porteuse d'un agrément national organisme "
                "d'accueil communautaire et d'activité solidaire"
            ),
        )
        OTHER = "OTHER", _("Autre")

    class AuthorizationStatus(models.TextChoices):
        NOT_SET = "NOT_SET", _("Habilitation en attente de validation")
        VALIDATED = "VALIDATED", _("Habilitation validée")
        REFUSED = "REFUSED", _("Validation de l'habilitation refusée")
        NOT_REQUIRED = "NOT_REQUIRED", _("Pas d'habilitation nécessaire")

    siret = models.CharField(verbose_name=_("Siret"), max_length=14, validators=[validate_siret], blank=True)
    kind = models.CharField(verbose_name=_("Type"), max_length=20, choices=Kind.choices, default=Kind.OTHER)
    name = models.CharField(verbose_name=_("Nom"), max_length=255)
    phone = models.CharField(verbose_name=_("Téléphone"), max_length=20, blank=True)
    email = models.EmailField(verbose_name=_("E-mail"), blank=True)
    website = models.URLField(verbose_name=_("Site web"), blank=True)
    description = models.TextField(verbose_name=_("Description"), blank=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Membres"),
        through="PrescriberMembership",
        blank=True,
        through_fields=("organization", "user"),
    )
    is_authorized = models.BooleanField(
        verbose_name=_("Habilitation"),
        default=False,
        help_text=_("Précise si l'organisation est habilitée par le Préfet."),
    )
    code_safir_pole_emploi = models.CharField(
        verbose_name=_("Code Safir"),
        help_text=_("Code unique d'une agence Pole emploi."),
        validators=[validate_code_safir],
        max_length=5,
        blank=True,
        # Empty values are stored as NULL if both `null=True` and `unique=True` are set.
        # This avoids unique constraint violations when saving multiple objects with blank values.
        null=True,
        unique=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Créé par"),
        related_name="created_prescriber_organization_set",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(verbose_name=_("Date de création"), default=timezone.now)
    updated_at = models.DateTimeField(verbose_name=_("Date de modification"), blank=True, null=True)

    authorization_status = models.CharField(
        verbose_name=_("Statut de l'habilitation"),
        max_length=20,
        choices=AuthorizationStatus.choices,
        default=AuthorizationStatus.NOT_SET,
    )
    authorization_updated_at = models.DateTimeField(
        verbose_name=_("Date de MAJ du statut de l'habilitation"), null=True
    )
    authorization_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Dernière MAJ de l'habilitation par"),
        related_name="authorization_status_set",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    objects = models.Manager.from_queryset(PrescriberOrganizationQuerySet)()

    class Meta:
        verbose_name = _("Organisation")
        verbose_name_plural = _("Organisations")

    def __str__(self):
        return f"{self.name}"

    def save(self, *args, **kwargs):
        if self.pk:
            self.updated_at = timezone.now()
        return super().save(*args, **kwargs)

    def clean(self, *args, **kwargs):
        super().clean()
        self.clean_code_safir_pole_emploi()
        self.clean_siret()

    def clean_code_safir_pole_emploi(self):
        """
        A code SAFIR can only be set for PE agencies.
        """
        if self.kind != self.Kind.PE and self.code_safir_pole_emploi:
            raise ValidationError({"code_safir_pole_emploi": _("Le Code Safir est réservé aux agences Pôle emploi.")})

    def clean_siret(self):
        """
        SIRET is required for all organizations, except for PE agencies.
        """
        if self.kind != self.Kind.PE:
            if not self.siret:
                raise ValidationError({"siret": _("Le SIRET est obligatoire.")})
            if self._meta.model.objects.filter(siret=self.siret).exclude(pk=self.pk).exists():
                raise ValidationError({"siret": _("Ce SIRET est déjà utilisé.")})

    @property
    def display_name(self):
        return self.name.capitalize()

    @property
    def has_members(self):
        return self.active_members.exists()

    @property
    def active_members(self):
        """
        In this context, active == has an active membership AND user is still active
        """
        return self.members.filter(is_active=True, prescribermembership__is_active=True)

    @property
    def deactivated_members(self):
        """
        List of previous members of the structure, still active as user (from the model POV)
        but deactivated by an admin at some point in time.
        """
        return self.members(is_active=True, prescribermembership__is_active=False)

    @property
    def active_admin_members(self):
        """
        Active admin members:
        active user/admin in this context means both:
        * user.is_active: user is able to do something on the platform
        * user.membership.is_active: is a member of this structure
        """
        return self.active_members.filter(prescribermembership__is_admin=True, prescribermembership__organization=self)

    def get_card_url(self):
        if not self.is_authorized:
            return None
        return reverse("prescribers_views:card", kwargs={"org_id": self.pk})

    def has_refused_authorization(self):
        return self.authorization_status == self.AuthorizationStatus.REFUSED

    def has_pending_authorization(self):
        """
        Pending manual verification of authorization by support staff.
        """
        return self.authorization_status == self.AuthorizationStatus.NOT_SET

    def has_pending_authorization_proof(self):
        """
        An unknown organization claiming to be authorized must provide a written proof.
        """
        return self.kind == self.Kind.OTHER and self.authorization_status == self.AuthorizationStatus.NOT_SET

    def get_admins(self):
        return self.members.filter(is_active=True, prescribermembership__is_admin=True)

    def new_signup_warning_email_to_existing_members(self, user):
        """
        Send a warning fyi-only email to all existing users of the organization
        about a new user signup.
        """
        to = [u.email for u in self.active_members]
        context = {"new_user": user, "organization": self}
        subject = "prescribers/email/new_signup_warning_email_to_existing_members_subject.txt"
        body = "prescribers/email/new_signup_warning_email_to_existing_members_body.txt"
        return get_email_message(to, context, subject, body)

    def validated_prescriber_organization_email(self):
        """
        Send an email to the user who asked for the validation
        of a new prescriber organization
        """
        to = [u.email for u in self.active_members]
        context = {"organization": self}
        subject = "prescribers/email/validated_prescriber_organization_email_subject.txt"
        body = "prescribers/email/validated_prescriber_organization_email_body.txt"
        return get_email_message(to, context, subject, body)

    def refused_prescriber_organization_email(self):
        """
        Send an email to the user who asked for the validation
        of a new prescriber organization when refused
        """
        to = [u.email for u in self.active_members]
        context = {"organization": self}
        subject = "prescribers/email/refused_prescriber_organization_email_subject.txt"
        body = "prescribers/email/refused_prescriber_organization_email_body.txt"
        return get_email_message(to, context, subject, body)

    def must_validate_prescriber_organization_email(self):
        """
        Send an email to the support:
        signup of a **newly created** prescriber organization, with unregistered/unchecked org
        => prescriber organization authorization must be validated
        """
        to = [settings.ITOU_EMAIL_CONTACT]
        context = {"organization": self}
        subject = "prescribers/email/must_validate_prescriber_organization_email_subject.txt"
        body = "prescribers/email/must_validate_prescriber_organization_email_body.txt"
        return get_email_message(to, context, subject, body)

    def new_member_deactivation_email(self, user):
        """
        Send email when an admin of the structure disable the membership of a given user (deactivation).
        """
        to = [user.email]
        context = {"organization": self}
        subject = "prescribers/email/new_member_deactivation_email_subject.txt"
        body = "prescribers/email/new_member_deactivation_email_body.txt"
        return get_email_message(to, context, subject, body)

    def new_member_activation_email(self, user):
        """
        Send email when an admin of the structure activate the membership of a given user.
        """
        to = [user.email]
        context = {"organization": self}
        subject = "prescribers/email/new_member_activation_email_subject.txt"
        body = "prescribers/email/new_member_activation_email_body.txt"
        return get_email_message(to, context, subject, body)

    def add_admin_email(self, user):
        """
        Send info email to a new admin of the organization (added)
        """
        to = [user.email]
        context = {"organization": self}
        subject = "prescribers/email/add_admin_email_subject.txt"
        body = "prescribers/email/add_admin_email_body.txt"
        return get_email_message(to, context, subject, body)

    def remove_admin_email(self, user):
        """
        Send info email to a former admin of the organization (removed)
        """
        to = [user.email]
        context = {"organization": self}
        subject = "prescribers/email/remove_admin_email_subject.txt"
        body = "prescribers/email/remove_admin_email_body.txt"
        return get_email_message(to, context, subject, body)


class PrescriberMembership(models.Model):
    """Intermediary model between `User` and `PrescriberOrganization`."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(PrescriberOrganization, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(verbose_name=_("Date d'adhésion"), default=timezone.now)
    is_admin = models.BooleanField(verbose_name=_("Administrateur de la structure d'accompagnement"), default=False)
    is_active = models.BooleanField(_("Rattachement actif"), default=True)
    updated_at = models.DateTimeField(verbose_name=_("Date de mise à jour"), null=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="prescriber_organization_membership_updated_by",
        null=True,
        on_delete=models.CASCADE,
        verbose_name=_("Mis à jour par"),
    )

    class Meta:
        unique_together = ("user_id", "organization_id")

    def toggle_user_membership(self, user):
        """
        Toggles the membership of a member (reference held by self)
        `user` is the admin updating this user (`updated_by` field)
        """
        assert user

        self.is_active = not self.is_active
        self.updated_at = timezone.now()
        self.updated_by = user
        return self.is_active

    def set_admin_role(self, active, user):
        """
        Set admin role for the given user.
        `user` is the admin updating this user (`updated_by` field)
        """
        assert user

        self.is_admin = active
        self.updated_at = timezone.now()
        self.updated_by = user
