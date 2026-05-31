"""Django settings for the project."""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-me-in-production")
GOOGLE_RECAPTCHA_SITE_KEY = os.getenv("GOOGLE_RECAPTCHA_SITE_KEY", "")
GOOGLE_RECAPTCHA_SECRET_KEY = os.getenv("GOOGLE_RECAPTCHA_SECRET_KEY", "")

# SECURITY WARNING: don't run with debug turned on in production!
if os.getenv("DJANGO_ENV") == "prod":
    DEBUG = False
    ALLOWED_HOSTS = ["*"]
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
else:
    DEBUG = True
    ALLOWED_HOSTS = ["*"]

# Application definition

INSTALLED_APPS = [
    "experiments.apps.ExperimentsConfig",
    "django.contrib.contenttypes",
    "grappelli.dashboard",
    "grappelli",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "colorfield",
    "tinymce",
    "easy_thumbnails",
    "filer",
]

SESSION_ENGINE = "django.contrib.sessions.backends.db"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "root": {"level": "INFO", "handlers": ["file"]},
    "handlers": {
        "console": {
            "level": "WARNING",
            "class": "logging.StreamHandler",
            "formatter": "app",
        },
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "django.log"),
            "backupCount": 10,  # keep at most 10 log files
            "maxBytes": 5242880,  # 5MB
            "formatter": "app",
        },
    },
    "loggers": {
        "django": {"handlers": ["file", "console"], "level": "INFO", "propagate": True},
    },
    "formatters": {
        "app": {
            "format": (
                "%(asctime)s [%(levelname)-8s] (%(module)s.%(funcName)s) %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
}

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "postgres"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
        "HOST": os.getenv("DB_HOST", "db"),
        "PORT": int(os.getenv("DB_PORT", "5432")),
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = "en-us"
"""
gettext = lambda x: x

LANGUAGE_CODE = 'de_DE'
LANGUAGES = (
    ('de', gettext('German')),
)
"""
TIME_ZONE = "UTC"  # Default

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Admin page customisations

GRAPPELLI_INDEX_DASHBOARD = "config.dashboard.CustomIndexDashboard"
GRAPPELLI_ADMIN_TITLE = "e-Babylab"

# Tinymce editor config

TINYMCE_DEFAULT_CONFIG = {
    "menubar": False,
    "relative_urls": False,
    "convert_urls": False,
    "remove_script_host": False,
    "forced_root_block": False,
    "plugins": "lists link image code",
    "toolbar": "undo redo | fontselect fontsizeselect | forecolor | bold italic underline | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | link image | code | removeformat",
    "fontsize_formats": "8pt 10pt 12pt 14pt 16pt 18pt 24pt 36pt 48pt",
    "extended_valid_elements": "script[language|type|src]",
}
X_FRAME_OPTIONS = "SAMEORIGIN"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

WEBCAM_URL = "/webcam/"
WEBCAM_ROOT = os.path.join(BASE_DIR, "webcam")

WEBCAM_TEST_URL = "/webcam-test/"
WEBCAM_TEST_ROOT = os.path.join(WEBCAM_ROOT, "test")

REPORTS_URL = "/reports/"
REPORTS_ROOT = os.path.join(BASE_DIR, "reports")

# Default auto field for models
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# File management settings
FILER_MIME_TYPES_WHITELIST = [
    # Audio
    "audio/mpeg",
    "audio/wav",
    # Documents
    "text/css",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/html",
    "application/pdf",
    "application/rtf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    # Images
    "image/gif",
    "image/jpeg",
    "image/png",
    # Video
    "video/mp4",
    "video/ogg",
    "video/webm",
]
FILER_STORAGES = {
    "public": {
        "main": {
            "ENGINE": "filer.storage.PublicFileSystemStorage",
            "OPTIONS": {
                "location": MEDIA_ROOT + "/uploads",
                "base_url": MEDIA_URL + "uploads/",
            },
            "UPLOAD_TO": "filer.utils.generate_filename.by_date",
            "UPLOAD_TO_PREFIX": "",
        },
    },
    "private": {
        "main": {
            "ENGINE": "filer.storage.PrivateFileSystemStorage",
            "OPTIONS": {
                "location": MEDIA_ROOT + "/filer_private",
                "base_url": "/smedia/filer_private/",
            },
            "UPLOAD_TO": "filer.utils.generate_filename.by_date",
            "UPLOAD_TO_PREFIX": "",
        },
    },
}
FILER_THUMBNAIL_ICON_SIZE = 60  # File browser grid view thumbnail size
THUMBNAIL_PRESERVE_EXTENSIONS = ["gif"]
