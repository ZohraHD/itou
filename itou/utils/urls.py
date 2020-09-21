import time

import jwt
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme


def get_safe_url(request, param_name, fallback_url=None):

    url = request.GET.get(param_name) or request.POST.get(param_name)

    allowed_hosts = settings.ALLOWED_HOSTS
    require_https = request.is_secure()

    if url:

        if settings.DEBUG:
            # In DEBUG mode the network location part `127.0.0.1:8000` contains
            # a port and fails the validation of `url_has_allowed_host_and_scheme`
            # since it's not a member of `allowed_hosts`:
            # https://github.com/django/django/blob/525274f/django/utils/http.py#L413
            # As a quick fix, we build a new URL without the port.
            from urllib.parse import ParseResult, urlparse

            url_info = urlparse(url)
            url_without_port = ParseResult(
                scheme=url_info.scheme,
                netloc=url_info.hostname,
                path=url_info.path,
                params=url_info.params,
                query=url_info.query,
                fragment=url_info.fragment,
            ).geturl()
            if url_has_allowed_host_and_scheme(url_without_port, allowed_hosts, require_https):
                return url

        else:
            if url_has_allowed_host_and_scheme(url, allowed_hosts, require_https):
                return url

    return fallback_url


def get_absolute_url(path=""):
    if path.startswith("/"):
        path = path[1:]
    return f"{settings.ITOU_PROTOCOL}://{settings.ITOU_FQDN}/{path}"


class SiretConverter:
    """
    Custom path converter for Siret.
    https://docs.djangoproject.com/en/dev/topics/http/urls/#registering-custom-path-converters
    """

    regex = "[0-9]{14}"

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return f"{value}"


# Metabase private / signed URLs
# See:
# * https://www.metabase.com/docs/latest/enterprise-guide/full-app-embedding.html
# * https://github.com/jpadilla/pyjwt
# * https://github.com/metabase/embedding-reference-apps/blob/master/django/embedded_analytics/user_stats/views.py
def _get_token(payload):
    return jwt.encode(payload, settings.METABASE_SECRET_KEY, algorithm="HS256").decode("utf8")


def metabase_embedded_url(dashboard_id):
    payload = {"resource": {"dashboard": dashboard_id}, "params": {}, "exp": round(time.time()) + (60 * 10)}
    return settings.METABASE_SITE_URL + "/embed/dashboard/" + _get_token(payload)
