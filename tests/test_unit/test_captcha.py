"""Tests for the pluggable CAPTCHA provider system."""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory, override_settings

from experiments.captcha import (
    AltchaProvider,
    NoneProvider,
    TrustSigProvider,
    TurnstileProvider,
    altcha_challenge_view,
    captcha_context,
    get_captcha_provider,
)

# ---------------------------------------------------------------------------
# Factory / auto-detection
# ---------------------------------------------------------------------------


class TestGetCaptchaProvider:
    """Tests for get_captcha_provider() factory."""

    @pytest.mark.parametrize(
        ("provider", "settings_override", "expected_cls"),
        [
            ("turnstile", {"CLOUDFLARE_TURNSTILE_SECRET_KEY": "k"}, TurnstileProvider),
            ("altcha", {"ALTCHA_HMAC_KEY": "k"}, AltchaProvider),
            ("trustsig", {"TRUSTSIG_SECRET_KEY": "k"}, TrustSigProvider),
            ("none", {}, NoneProvider),
            ("", {}, AltchaProvider),
        ],
        ids=["turnstile", "altcha", "trustsig", "none", "default-altcha"],
    )
    def test_returns_correct_provider(self, provider, settings_override, expected_cls):
        with override_settings(CAPTCHA_PROVIDER=provider, **settings_override):
            assert isinstance(get_captcha_provider(), expected_cls)

    def test_raises_on_unknown_provider(self):
        with (
            override_settings(CAPTCHA_PROVIDER="bogus"),
            pytest.raises(ValueError, match="Unknown CAPTCHA_PROVIDER"),
        ):
            get_captcha_provider()


# ---------------------------------------------------------------------------
# TurnstileProvider
# ---------------------------------------------------------------------------


class TestTurnstileProvider:
    """Tests for TurnstileProvider."""

    @override_settings(CLOUDFLARE_TURNSTILE_SECRET_KEY="secret")
    def test_is_enabled(self):
        assert TurnstileProvider().is_enabled()

    @override_settings(CLOUDFLARE_TURNSTILE_SECRET_KEY="")
    def test_is_disabled_when_no_key(self):
        assert not TurnstileProvider().is_enabled()

    @override_settings(CLOUDFLARE_TURNSTILE_SECRET_KEY="")
    def test_verify_bypassed_when_disabled(self):
        assert TurnstileProvider().verify({})

    @override_settings(CLOUDFLARE_TURNSTILE_SECRET_KEY="secret")
    @patch("experiments.captcha.requests.post")
    def test_verify_success(self, mock_post):
        mock_post.return_value.json.return_value = {"success": True}
        assert TurnstileProvider().verify({"cf-turnstile-response": "token"})
        mock_post.assert_called_once()

    @override_settings(CLOUDFLARE_TURNSTILE_SECRET_KEY="secret")
    @patch("experiments.captcha.requests.post")
    def test_verify_failure(self, mock_post):
        mock_post.return_value.json.return_value = {"success": False}
        assert not TurnstileProvider().verify({"cf-turnstile-response": "token"})

    @override_settings(CLOUDFLARE_TURNSTILE_SECRET_KEY="secret")
    @patch("experiments.captcha.requests.post", side_effect=Exception("timeout"))
    def test_verify_exception_returns_false(self, mock_post):
        assert not TurnstileProvider().verify({"cf-turnstile-response": "token"})

    @override_settings(CLOUDFLARE_TURNSTILE_SITE_KEY="pk_test")
    def test_widget_html_contains_site_key(self):
        html = TurnstileProvider().get_widget_html()
        assert "pk_test" in html
        assert "cf-turnstile" in html

    def test_post_field_name(self):
        assert TurnstileProvider().get_post_field_name() == "cf-turnstile-response"

    def test_form_attrs(self):
        assert TurnstileProvider().get_form_attrs() == {
            "data-captcha-provider": "turnstile"
        }


# ---------------------------------------------------------------------------
# AltchaProvider
# ---------------------------------------------------------------------------


class TestAltchaProvider:
    """Tests for AltchaProvider."""

    @override_settings(ALTCHA_HMAC_KEY="secret")
    def test_is_enabled(self):
        assert AltchaProvider().is_enabled()

    @override_settings(ALTCHA_HMAC_KEY="")
    def test_is_disabled_when_no_key(self):
        assert not AltchaProvider().is_enabled()

    @override_settings(ALTCHA_HMAC_KEY="")
    def test_verify_bypassed_when_disabled(self):
        assert AltchaProvider().verify({})

    @override_settings(ALTCHA_HMAC_KEY="secret")
    def test_verify_empty_payload_returns_false(self):
        assert not AltchaProvider().verify({"altcha": ""})

    @override_settings(ALTCHA_HMAC_KEY="secret")
    @patch("altcha.verify_solution")
    def test_verify_success(self, mock_verify):
        mock_verify.return_value = MagicMock(verified=True, expired=False)
        assert AltchaProvider().verify({"altcha": "payload"})

    @override_settings(ALTCHA_HMAC_KEY="secret")
    @patch("altcha.verify_solution")
    def test_verify_expired_returns_false(self, mock_verify):
        mock_verify.return_value = MagicMock(verified=True, expired=True)
        assert not AltchaProvider().verify({"altcha": "payload"})

    @override_settings(ALTCHA_HMAC_KEY="secret")
    @patch("altcha.verify_solution")
    def test_verify_invalid_returns_false(self, mock_verify):
        mock_verify.return_value = MagicMock(verified=False, expired=False)
        assert not AltchaProvider().verify({"altcha": "payload"})

    @override_settings(ALTCHA_HMAC_KEY="secret")
    @patch("altcha.verify_solution", side_effect=Exception("fail"))
    def test_verify_exception_returns_false(self, mock_verify):
        assert not AltchaProvider().verify({"altcha": "payload"})

    def test_widget_html_contains_challengeurl(self):
        html = AltchaProvider().get_widget_html()
        assert "challengeurl" in html
        assert "altcha-widget" in html

    def test_post_field_name(self):
        assert AltchaProvider().get_post_field_name() == "altcha"

    def test_scripts_html_contains_altcha_cdn(self):
        html = AltchaProvider().get_scripts_html()
        assert "altcha.min.js" in html

    def test_form_attrs(self):
        assert AltchaProvider().get_form_attrs() == {"data-captcha-provider": "altcha"}


# ---------------------------------------------------------------------------
# TrustSigProvider
# ---------------------------------------------------------------------------


class TestTrustSigProvider:
    """Tests for TrustSigProvider. Verifies fail-closed behaviour."""

    @override_settings(TRUSTSIG_SECRET_KEY="sk_live_test")
    def test_is_enabled(self):
        assert TrustSigProvider().is_enabled()

    @override_settings(TRUSTSIG_SECRET_KEY="")
    def test_is_disabled_when_no_key(self):
        assert not TrustSigProvider().is_enabled()

    @override_settings(TRUSTSIG_SECRET_KEY="")
    def test_verify_bypassed_when_disabled(self):
        assert TrustSigProvider().verify({})

    @override_settings(TRUSTSIG_SECRET_KEY="sk_live_test")
    def test_verify_missing_token_returns_false(self):
        assert not TrustSigProvider().verify({})

    @override_settings(TRUSTSIG_SECRET_KEY="sk_live_test")
    @patch("experiments.captcha.requests.post")
    def test_verify_allow(self, mock_post):
        mock_post.return_value.json.return_value = {
            "action": "ALLOW",
            "is_bot": False,
            "score": 5,
        }
        assert TrustSigProvider().verify({"trustsig-response": "token"})

    @override_settings(TRUSTSIG_SECRET_KEY="sk_live_test")
    @patch("experiments.captcha.requests.post")
    def test_verify_block_returns_false(self, mock_post):
        mock_post.return_value.json.return_value = {
            "action": "BLOCK",
            "is_bot": True,
            "score": 90,
        }
        assert not TrustSigProvider().verify({"trustsig-response": "token"})

    @override_settings(TRUSTSIG_SECRET_KEY="sk_live_test")
    @patch("experiments.captcha.requests.post")
    def test_verify_challenge_returns_false(self, mock_post):
        """CHALLENGE verdict must also be rejected (fail closed)."""
        mock_post.return_value.json.return_value = {
            "action": "CHALLENGE",
            "is_bot": False,
            "score": 50,
        }
        assert not TrustSigProvider().verify({"trustsig-response": "token"})

    @override_settings(TRUSTSIG_SECRET_KEY="sk_live_test")
    @patch("experiments.captcha.requests.post", side_effect=Exception("timeout"))
    def test_verify_exception_returns_false(self, mock_post):
        """Network errors must fail closed."""
        assert not TrustSigProvider().verify({"trustsig-response": "token"})

    @override_settings(TRUSTSIG_SITE_KEY="pk_live_test")
    def test_scripts_html_contains_site_key(self):
        html = TrustSigProvider().get_scripts_html()
        assert "pk_live_test" in html
        assert "trustsig.js" in html
        assert "data-auto-scan" in html

    def test_widget_html_is_empty(self):
        assert TrustSigProvider().get_widget_html() == ""

    def test_post_field_name(self):
        assert TrustSigProvider().get_post_field_name() == "trustsig-response"

    def test_form_attrs(self):
        assert TrustSigProvider().get_form_attrs() == {
            "data-captcha-provider": "trustsig"
        }


# ---------------------------------------------------------------------------
# NoneProvider
# ---------------------------------------------------------------------------


class TestNoneProvider:
    """Tests for NoneProvider."""

    def test_is_not_enabled(self):
        assert not NoneProvider().is_enabled()

    def test_verify_always_true(self):
        assert NoneProvider().verify({})

    def test_widget_html_empty(self):
        assert NoneProvider().get_widget_html() == ""

    def test_scripts_html_empty(self):
        assert NoneProvider().get_scripts_html() == ""

    def test_form_attrs_empty(self):
        assert NoneProvider().get_form_attrs() == {}

    def test_post_field_name_empty(self):
        assert NoneProvider().get_post_field_name() == ""


# ---------------------------------------------------------------------------
# captcha_context helper
# ---------------------------------------------------------------------------


class TestCaptchaContext:
    """Tests for the captcha_context() helper."""

    @override_settings(CAPTCHA_PROVIDER="none")
    def test_none_provider_returns_empty_strings(self):
        ctx = captcha_context()
        assert ctx["captcha_form_attrs"] == ""
        assert ctx["captcha_widget"] == ""
        assert ctx["captcha_scripts"] == ""

    @override_settings(
        CAPTCHA_PROVIDER="turnstile",
        CLOUDFLARE_TURNSTILE_SECRET_KEY="s",
        CLOUDFLARE_TURNSTILE_SITE_KEY="pk",
    )
    def test_turnstile_returns_populated_context(self):
        ctx = captcha_context()
        assert "data-captcha-provider" in str(ctx["captcha_form_attrs"])
        assert "cf-turnstile" in str(ctx["captcha_widget"])
        assert "turnstile" in str(ctx["captcha_scripts"])


# ---------------------------------------------------------------------------
# ALTCHA challenge view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAltchaChallengeView:
    """Tests for the altcha_challenge_view endpoint."""

    @override_settings(ALTCHA_HMAC_KEY="test-hmac-key-for-challenge")
    def test_returns_json_challenge(self):
        factory = RequestFactory()
        request = factory.get("/captcha/challenge")
        response = altcha_challenge_view(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert "parameters" in data
        assert data["parameters"]["algorithm"] == "SHA-256"
        assert "signature" in data
