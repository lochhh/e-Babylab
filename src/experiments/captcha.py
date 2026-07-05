"""Pluggable CAPTCHA provider system.

Supports multiple providers selectable via the CAPTCHA_PROVIDER env var:
altcha (default), turnstile, trustsig, none.
"""

import logging
from abc import ABC, abstractmethod

import requests
from django.conf import settings
from django.core.checks import Error, register
from django.http import JsonResponse
from django.templatetags.static import static
from django.utils.safestring import mark_safe

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, type["CaptchaProvider"]] = {}


def _register(name: str):
    """Decorate a provider class `name` to be registered."""

    def decorator(cls):
        _REGISTRY[name] = cls
        return cls

    return decorator


def get_captcha_provider() -> "CaptchaProvider":
    """Return the configured CAPTCHA provider instance.

    Reads ``settings.CAPTCHA_PROVIDER``; defaults to ``"altcha"`` when unset.
    """
    provider_name = getattr(settings, "CAPTCHA_PROVIDER", "") or "altcha"

    if provider_name not in _REGISTRY:
        valid = ", ".join(sorted(_REGISTRY))
        raise ValueError(
            f"Unknown CAPTCHA_PROVIDER: {provider_name!r}. Valid choices: {valid}"
        )
    return _REGISTRY[provider_name]()


def captcha_context() -> dict[str, str]:
    """Build template context for the active CAPTCHA provider."""
    provider = get_captcha_provider()
    if not provider.is_enabled():
        return {"captcha_form_attrs": "", "captcha_widget": "", "captcha_scripts": ""}
    attrs = " ".join(f'{k}="{v}"' for k, v in provider.get_form_attrs().items())
    return {
        "captcha_form_attrs": mark_safe(attrs),
        "captcha_widget": mark_safe(provider.get_widget_html()),
        "captcha_scripts": mark_safe(provider.get_scripts_html()),
    }


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class CaptchaProvider(ABC):
    """Strategy interface for CAPTCHA providers."""

    @abstractmethod
    def is_enabled(self) -> bool:
        """Return True if this provider is configured and active."""

    @abstractmethod
    def get_widget_html(self) -> str:
        """Return the HTML snippet for the CAPTCHA widget."""

    @abstractmethod
    def get_scripts_html(self) -> str:
        """Return ``<script>`` tags needed by this provider."""

    @abstractmethod
    def get_form_attrs(self) -> dict[str, str]:
        """Return extra ``data-*`` attributes for the ``<form>`` tag."""

    @abstractmethod
    def verify(self, request_post: dict) -> bool:
        """Server-side verification of the CAPTCHA response token."""

    @abstractmethod
    def get_post_field_name(self) -> str:
        """Return the POST field name that carries the response token."""


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


@_register("turnstile")
class TurnstileProvider(CaptchaProvider):
    """Cloudflare Turnstile — mostly invisible, hosted by Cloudflare (US)."""

    def is_enabled(self):
        return bool(
            getattr(settings, "CLOUDFLARE_TURNSTILE_SECRET_KEY", "")
            and getattr(settings, "CLOUDFLARE_TURNSTILE_SITE_KEY", "")
        )

    def get_widget_html(self):
        site_key = getattr(settings, "CLOUDFLARE_TURNSTILE_SITE_KEY", "")
        return (
            f'<div class="cf-turnstile captcha-badge" '
            f'data-sitekey="{site_key}" data-size="compact" '
            f'data-execution="execute" data-callback="onCaptchaVerified"></div>'
        )

    def get_scripts_html(self):
        handler_url = static("experiments/js/captcha-handler.js")
        return (
            "<script src='https://challenges.cloudflare.com/turnstile/v0/api.js' "
            "async defer></script>\n"
            f'<script type="module" src="{handler_url}"></script>'
        )

    def get_form_attrs(self):
        return {"data-captcha-provider": "turnstile"}

    def verify(self, request_post):
        if not self.is_enabled():
            return True
        token = request_post.get("cf-turnstile-response", "")
        try:
            result = requests.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": settings.CLOUDFLARE_TURNSTILE_SECRET_KEY,
                    "response": token,
                },
                timeout=10,
            ).json()
            return result.get("success", False)
        except Exception:
            logger.exception("Turnstile verification request failed")
            return False

    def get_post_field_name(self):
        return "cf-turnstile-response"


@_register("altcha")
class AltchaProvider(CaptchaProvider):
    """ALTCHA — self-hosted proof-of-work, no third-party requests."""

    def is_enabled(self):
        return bool(getattr(settings, "ALTCHA_HMAC_KEY", ""))

    def get_widget_html(self):
        return (
            '<altcha-widget challengeurl="/captcha/challenge" '
            'name="altcha" auto="onsubmit" '
            'class="captcha-badge"></altcha-widget>'
        )

    def get_scripts_html(self):
        return (
            '<script async defer type="module" '
            'src="https://cdn.jsdelivr.net/npm/altcha/dist/altcha.min.js"></script>'
        )

    def get_form_attrs(self):
        return {"data-captcha-provider": "altcha"}

    def verify(self, request_post):
        if not self.is_enabled():
            return True
        payload = request_post.get("altcha", "")
        if not payload:
            return False
        try:
            import altcha

            result = altcha.verify_solution(
                payload, hmac_secret=settings.ALTCHA_HMAC_KEY
            )
            return result.verified and not result.expired
        except Exception:
            logger.exception("ALTCHA verification failed")
            return False

    def get_post_field_name(self):
        return "altcha"


@_register("trustsig")
class TrustSigProvider(CaptchaProvider):
    """TrustSig — invisible hardware-signal verification, EU-hosted (Germany).

    Fails closed: only ``action == "ALLOW"`` passes.
    """

    def is_enabled(self):
        return bool(
            getattr(settings, "TRUSTSIG_SECRET_KEY", "")
            and getattr(settings, "TRUSTSIG_SITE_KEY", "")
        )

    def get_widget_html(self):
        return ""

    def get_scripts_html(self):
        site_key = getattr(settings, "TRUSTSIG_SITE_KEY", "")
        return (
            f'<script src="https://edge.trustsig.eu/trustsig.js" '
            f'data-site-key="{site_key}" data-auto-scan="true"></script>'
        )

    def get_form_attrs(self):
        return {"data-captcha-provider": "trustsig"}

    def verify(self, request_post):
        if not self.is_enabled():
            return True
        token = request_post.get("trustsig-response", "")
        if not token:
            return False
        try:
            result = requests.post(
                "https://edge.trustsig.eu/verify",
                json={
                    "secret": settings.TRUSTSIG_SECRET_KEY,
                    "token": token,
                },
                timeout=10,
            ).json()
            return result.get("action") == "ALLOW"
        except Exception:
            logger.exception("TrustSig verification request failed")
            return False

    def get_post_field_name(self):
        return "trustsig-response"


@_register("none")
class NoneProvider(CaptchaProvider):
    """No CAPTCHA — verification always passes."""

    def is_enabled(self):
        return False

    def get_widget_html(self):
        return ""

    def get_scripts_html(self):
        return ""

    def get_form_attrs(self):
        return {}

    def verify(self, request_post):
        return True

    def get_post_field_name(self):
        return ""


# ---------------------------------------------------------------------------
# ALTCHA challenge endpoint
# ---------------------------------------------------------------------------


def altcha_challenge_view(request):
    """Return a fresh ALTCHA proof-of-work challenge as JSON."""
    import altcha

    challenge = altcha.create_challenge(
        algorithm="SHA-256",
        cost=50000,
        hmac_secret=settings.ALTCHA_HMAC_KEY,
    )
    return JsonResponse(challenge.to_dict())


@register()
def check_captcha_config(app_configs, **kwargs):
    """Error if the selected CAPTCHA provider is missing its required key(s).

    Each provider's ``is_enabled()`` silently no-ops verification rather than
    raising, so a missing key would otherwise fail open with no warning.
    """
    try:
        provider = get_captcha_provider()
    except ValueError as exc:
        return [Error(str(exc), id="experiments.E001")]

    provider_name = getattr(settings, "CAPTCHA_PROVIDER", "") or "altcha"

    if isinstance(provider, NoneProvider) or provider.is_enabled():
        return []

    return [
        Error(
            f"CAPTCHA_PROVIDER={provider_name!r} is set but its required key(s) "
            "are missing, so CAPTCHA verification is silently disabled.",
            hint="Set the provider's key(s) in .env, or use CAPTCHA_PROVIDER=none.",
            id="experiments.E002",
        )
    ]
