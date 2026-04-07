from functools import wraps
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import resolve_url


def user_passes_test(
    test_func, next_url=None, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME
):
    """Check whether the user passes a given test in order to access the view.

    Redirects to the login page if the test fails. Supports an optional
    ``next_url`` to redirect to after successful login.

    Args:
        test_func: A callable that takes a user object and returns ``True``
            if the user is permitted to access the view.
        next_url: URL to redirect to after login. Defaults to the current request path.
        login_url: URL of the login page. Defaults to ``settings.LOGIN_URL``.
        redirect_field_name: Name of the query parameter used to pass the
            next URL. Defaults to ``REDIRECT_FIELD_NAME``.

    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            path = request.build_absolute_uri()
            resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
            # If the login url is the same scheme and net location then just
            # use the path as the "next" url.
            login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
            current_scheme, current_netloc = urlparse(path)[:2]
            if (not login_scheme or login_scheme == current_scheme) and (
                not login_netloc or login_netloc == current_netloc
            ):
                path = request.get_full_path()
            resolved_next_url = resolve_url(next_url or path)
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(
                resolved_next_url, resolved_login_url, redirect_field_name
            )

        return _wrapped_view

    return decorator


def login_required(
    function=None,
    next_url=None,
    redirect_field_name=REDIRECT_FIELD_NAME,
    login_url=None,
):
    """Require the user to be authenticated to access the view.

    Redirects to the login page if the user is not logged in. Supports an
    optional ``next_url`` to redirect to after successful login.

    Args:
        function: The view function to decorate. If provided, the decorator
            is applied immediately.
        next_url: URL to redirect to after login. Defaults to the current request path.
        redirect_field_name: Name of the query parameter used to pass the
            next URL. Defaults to ``REDIRECT_FIELD_NAME``.
        login_url: URL of the login page. Defaults to ``settings.LOGIN_URL``.

    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated,
        next_url=next_url,
        login_url=login_url,
        redirect_field_name=redirect_field_name,
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
