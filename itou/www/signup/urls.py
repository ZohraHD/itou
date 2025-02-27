from django.urls import path
from django.views.generic import TemplateView

from itou.www.signup import views


# https://docs.djangoproject.com/en/dev/topics/http/urls/#url-namespaces-and-included-urlconfs
app_name = "signup"

urlpatterns = [
    # Job seeker.
    path("job_seeker", views.JobSeekerSignupView.as_view(), name="job_seeker"),
    path("job_seeker/nir", views.job_seeker_nir, name="job_seeker_nir"),
    path("job_seeker/situation", views.job_seeker_situation, name="job_seeker_situation"),
    path(
        "job_seeker/situation_not_eligible",
        TemplateView.as_view(template_name="signup/job_seeker_situation_not_eligible.html"),
        name="job_seeker_situation_not_eligible",
    ),
    # Prescriber.
    path(
        "prescriber/check_already_exists",
        views.prescriber_check_already_exists,
        name="prescriber_check_already_exists",
    ),
    path(
        "prescriber/request_invitation/<int:membership_id>",
        views.prescriber_request_invitation,
        name="prescriber_request_invitation",
    ),
    path(
        "prescriber/choose_org",
        views.prescriber_choose_org,
        name="prescriber_choose_org",
    ),
    path(
        "prescriber/choose_kind",
        views.prescriber_choose_kind,
        name="prescriber_choose_kind",
    ),
    path(
        "prescriber/confirm_authorization",
        views.prescriber_confirm_authorization,
        name="prescriber_confirm_authorization",
    ),
    path(
        "prescriber/pole_emploi/safir",
        views.prescriber_pole_emploi_safir_code,
        name="prescriber_pole_emploi_safir_code",
    ),
    path(
        "prescriber/pole_emploi/user",
        views.PrescriberPoleEmploiUserSignupView.as_view(),
        name="prescriber_pole_emploi_user",
    ),
    path(
        "prescriber/user",
        views.PrescriberUserSignupView.as_view(),
        name="prescriber_user",
    ),
    # SIAE.
    path("siae/select", views.siae_select, name="siae_select"),
    path("siae/<str:encoded_siae_id>/<str:token>", views.SiaeSignupView.as_view(), name="siae"),
]
