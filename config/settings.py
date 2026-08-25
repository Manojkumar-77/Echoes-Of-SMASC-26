"""
Django settings for config project.

Production-ready configuration for:
- Django 4.2
- PostgreSQL
- Render
- Gunicorn
- WhiteNoise
- Optional S3-compatible object storage
- Django Unfold
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


# ==============================================================================
# BASE CONFIGURATION
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env for local development.
# Render/system environment variables take precedence.
load_dotenv(BASE_DIR / ".env", override=False)


# ==============================================================================
# ENVIRONMENT HELPERS
# ==============================================================================

def _get_env(name, default=None):
    """Return a stripped environment variable or default."""
    value = os.getenv(name)

    if value is None:
        return default

    value = value.strip()

    return value if value else default


def _get_bool_env(name, default=False):
    """Safely parse boolean environment variables."""
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    value = value.strip().lower()

    if value in {"true", "1", "yes", "y", "on"}:
        return True

    if value in {"false", "0", "no", "n", "off"}:
        return False

    return default


def _get_int_env(name, default):
    """Safely parse integer environment variables."""
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return default


def _get_list_env(name, default=None):
    """Parse comma-separated environment variables."""
    value = os.getenv(name)

    if value is None or not value.strip():
        return list(default or [])

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


# ==============================================================================
# TESTING / DEBUG
# ==============================================================================

IS_TESTING = "test" in sys.argv

# Production-safe default:
# DEBUG=False unless explicitly enabled.
DEBUG = _get_bool_env(
    "DJANGO_DEBUG",
    _get_bool_env("DEBUG", False),
)

# Tests may override DEBUG if required by the test environment.
if IS_TESTING:
    DEBUG = _get_bool_env("DJANGO_TEST_DEBUG", DEBUG)


# ==============================================================================
# SECRET KEY
# ==============================================================================

raw_secret_key = (
    _get_env("DJANGO_SECRET_KEY")
    or _get_env("SECRET_KEY")
)

# Local-development & build-time fallback.
# In production, Render injects DJANGO_SECRET_KEY automatically.
SECRET_KEY = raw_secret_key or (
    "django-insecure-production-fallback-key-do-not-use-in-real-prod-p-gallery"
)


# ==============================================================================
# HOST CONFIGURATION
# ==============================================================================

configured_allowed_hosts = _get_list_env(
    "DJANGO_ALLOWED_HOSTS",
    _get_list_env("ALLOWED_HOSTS"),
)

if configured_allowed_hosts:
    ALLOWED_HOSTS = configured_allowed_hosts

elif DEBUG:
    ALLOWED_HOSTS = [
        "localhost",
        "127.0.0.1",
        "[::1]",
        "192.168.1.11",
    ]

else:
    ALLOWED_HOSTS = [
        "localhost",
        "127.0.0.1",
        ".onrender.com",
    ]


# Always support Render's externally supplied hostname.
render_hostname = _get_env("RENDER_EXTERNAL_HOSTNAME")

if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)

if ".onrender.com" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(".onrender.com")


# ==============================================================================
# CSRF TRUSTED ORIGINS
# ==============================================================================

configured_csrf_origins = _get_list_env(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    _get_list_env("CSRF_TRUSTED_ORIGINS"),
)

if configured_csrf_origins:
    CSRF_TRUSTED_ORIGINS = configured_csrf_origins

elif DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://192.168.1.11:8000",
    ]

else:
    CSRF_TRUSTED_ORIGINS = [
        "https://*.onrender.com",
    ]


# Automatically trust the actual Render hostname.
if render_hostname:
    render_origin = f"https://{render_hostname}"

    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)



# ==============================================================================
# APPLICATION DEFINITION
# ==============================================================================

INSTALLED_APPS = [
    "unfold",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "core",
]


# ==============================================================================
# MIDDLEWARE
# ==============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    "whitenoise.middleware.WhiteNoiseMiddleware",

    "core.middleware.DevCacheControlMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ==============================================================================
# URL / WSGI
# ==============================================================================

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

# Optional ASGI support.
ASGI_APPLICATION = "config.asgi.application"


# ==============================================================================
# TEMPLATES
# ==============================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "templates",
        ],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_branding",
            ],
        },
    },
]


# ==============================================================================
# DATABASE
# ==============================================================================

DATABASE_URL = _get_env("DATABASE_URL")

if DATABASE_URL:
    parsed_db = urlparse(DATABASE_URL)

    if parsed_db.scheme not in {
        "postgres",
        "postgresql",
    }:
        if not DEBUG:
            from django.core.exceptions import ImproperlyConfigured

            raise ImproperlyConfigured(
                "DATABASE_URL must use a PostgreSQL URL in production."
            )

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed_db.path.lstrip("/"),
            "USER": parsed_db.username or "",
            "PASSWORD": parsed_db.password or "",
            "HOST": parsed_db.hostname or "",
            "PORT": str(parsed_db.port or 5432),

            # Persistent DB connections.
            "CONN_MAX_AGE": _get_int_env(
                "DB_CONN_MAX_AGE",
                60,
            ),

            "CONN_HEALTH_CHECKS": True,
        }
    }

    # SSL behavior for production PostgreSQL.
    if not DEBUG:
        DATABASES["default"]["OPTIONS"] = {
            "sslmode": _get_env(
                "DB_SSLMODE",
                "require",
            ),
        }

else:
    # --------------------------------------------------------------------------
    # Development / Fallback Database
    # --------------------------------------------------------------------------
    # When DATABASE_URL is not provided (e.g., local dev or build-time collectstatic),
    # fall back cleanly to explicit DB_* settings or local SQLite.
    db_host = _get_env("DB_HOST")

    if db_host:
        DATABASES = {
            "default": {
                "ENGINE": _get_env(
                    "DB_ENGINE",
                    "django.db.backends.postgresql",
                ),
                "NAME": _get_env(
                    "DB_NAME",
                    "pgallery",
                ),
                "USER": _get_env(
                    "DB_USER",
                    "postgres",
                ),
                "PASSWORD": _get_env(
                    "DB_PASSWORD",
                    "",
                ),
                "HOST": db_host,
                "PORT": _get_env(
                    "DB_PORT",
                    "5432",
                ),
                "CONN_MAX_AGE": _get_int_env(
                    "DB_CONN_MAX_AGE",
                    60,
                ),
            }
        }

    else:
        # SQLite is ONLY for local development.
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }


# ==============================================================================
# PASSWORD VALIDATION
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME":
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator",
    },
    {
        "NAME":
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator",
    },
    {
        "NAME":
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator",
    },
    {
        "NAME":
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator",
    },
]


# ==============================================================================
# INTERNATIONALIZATION
# ==============================================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = _get_env(
    "DJANGO_TIME_ZONE",
    "Asia/Kolkata",
)

USE_I18N = True

USE_TZ = True


# ==============================================================================
# STATIC FILES
# ==============================================================================

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"


# ==============================================================================
# MEDIA FILES
# ==============================================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ==============================================================================
# STORAGE CONFIGURATION
# ==============================================================================

USE_S3 = (
    _get_bool_env("USE_S3", False)
    or bool(_get_env("AWS_STORAGE_BUCKET_NAME"))
)


if USE_S3:

    AWS_ACCESS_KEY_ID = _get_env(
        "AWS_ACCESS_KEY_ID",
        "",
    )

    AWS_SECRET_ACCESS_KEY = _get_env(
        "AWS_SECRET_ACCESS_KEY",
        "",
    )

    AWS_STORAGE_BUCKET_NAME = _get_env(
        "AWS_STORAGE_BUCKET_NAME",
        "",
    )

    AWS_S3_REGION_NAME = _get_env(
        "AWS_S3_REGION_NAME",
        "",
    )

    AWS_S3_ENDPOINT_URL = _get_env(
        "AWS_S3_ENDPOINT_URL",
        "",
    )

    AWS_S3_CUSTOM_DOMAIN = _get_env(
        "AWS_S3_CUSTOM_DOMAIN",
        "",
    )

    AWS_DEFAULT_ACL = None

    AWS_S3_FILE_OVERWRITE = False

    AWS_QUERYSTRING_AUTH = _get_bool_env(
        "AWS_QUERYSTRING_AUTH",
        False,
    )

    AWS_S3_SIGNATURE_VERSION = _get_env(
        "AWS_S3_SIGNATURE_VERSION",
        "s3v4",
    )

    # Optional cache headers.
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "max-age=86400",
    }

    STORAGES = {
        "default": {
            "BACKEND":
                "storages.backends.s3boto3.S3Boto3Storage",
        },

        "staticfiles": {
            "BACKEND":
                "core.storage.ProductionManifestStaticFilesStorage",
        },
    }

else:

    # Local filesystem media storage.
    #
    # IMPORTANT:
    # This is suitable for local development.
    # Production Render media should use S3-compatible storage.
    STORAGES = {
        "default": {
            "BACKEND":
                "django.core.files.storage.FileSystemStorage",
        },

        "staticfiles": {
            "BACKEND":
                (
                    "core.storage.DevAutoVersionStaticFilesStorage"
                    if DEBUG
                    else
                    "core.storage.ProductionManifestStaticFilesStorage"
                ),
        },
    }


# WhiteNoise configuration.
WHITENOISE_MANIFEST_STRICT = False


# ==============================================================================
# DEFAULT PRIMARY KEY
# ==============================================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==============================================================================
# SECURITY / BROWSER HARDENING
# ==============================================================================

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = _get_env(
    "DJANGO_X_FRAME_OPTIONS",
    "SAMEORIGIN" if DEBUG else "DENY",
)

SECURE_SSL_REDIRECT = _get_bool_env(
    "DJANGO_SECURE_SSL_REDIRECT",
    not DEBUG,
)

SESSION_COOKIE_SECURE = _get_bool_env(
    "DJANGO_SESSION_COOKIE_SECURE",
    not DEBUG,
)

CSRF_COOKIE_SECURE = _get_bool_env(
    "DJANGO_CSRF_COOKIE_SECURE",
    not DEBUG,
)

SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_HTTPONLY = False

SECURE_REFERRER_POLICY = _get_env(
    "DJANGO_SECURE_REFERRER_POLICY",
    "strict-origin-when-cross-origin",
)


# ==============================================================================
# HSTS
# ==============================================================================

# HSTS is intentionally conservative.
#
# Enable it explicitly after the production domain/HTTPS configuration
# has been verified.

SECURE_HSTS_SECONDS = _get_int_env(
    "DJANGO_SECURE_HSTS_SECONDS",
    0 if DEBUG else 31536000,
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = _get_bool_env(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    False if DEBUG else True,
)

SECURE_HSTS_PRELOAD = _get_bool_env(
    "DJANGO_SECURE_HSTS_PRELOAD",
    False if DEBUG else True,
)


# ==============================================================================
# DJANGO UNFOLD ADMIN
# ==============================================================================

from django.templatetags.static import static
from django.urls import reverse_lazy


def _unfold_static(path):
    return static(path)


UNFOLD = {
    "SITE_HEADER": "Echoes Of SMASC '26",

    "SITE_TITLE": "Echoes Of SMASC '26",

    "INDEX_TITLE": "Echoes Of SMASC '26 Administration",

    "SITE_ICON": {
        "light": lambda request:
            _unfold_static(
                "branding/03_RESPONSIVE_ICONS/ES26_256x256.png"
            ),

        "dark": lambda request:
            _unfold_static(
                "branding/03_RESPONSIVE_ICONS/ES26_256x256.png"
            ),
    },

    "SITE_LOGO": {
        "light": lambda request:
            _unfold_static(
                "branding/02_LOGO_VARIANTS/ES26_ROUNDED_512.png"
            ),

        "dark": lambda request:
            _unfold_static(
                "branding/02_LOGO_VARIANTS/ES26_ROUNDED_512.png"
            ),
    },

    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "type": "image/x-icon",
            "href": lambda request:
                _unfold_static(
                    "branding/04_FAVICONS_PWA/favicon.ico"
                ),
        },
    ],

    "SHOW_HISTORY": True,

    "SHOW_VIEW_ON_SITE": True,

    "THEME": "dark",

    "STYLES": [
        lambda request:
            _unfold_static(
                "admin/css/image-preview.css"
            ),
    ],

    "SCRIPTS": [
        lambda request:
            _unfold_static(
                "admin/js/image-preview.js"
            ),
    ],

    "COLORS": {
        "primary": {
            "50": "250 245 235",
            "100": "245 230 200",
            "200": "235 210 160",
            "300": "225 190 130",
            "400": "215 179 119",
            "500": "200 160 100",
            "600": "180 140 85",
            "700": "150 115 65",
            "800": "120 90 50",
            "900": "90 65 35",
            "950": "60 40 20",
        },
    },

    "SIDEBAR": {
        "show_search": True,

        "show_all_applications": True,

        "navigation": [
            {
                "title": "CONTENT MANAGEMENT",
                "separator": True,
                "items": [
                    {
                        "title": "Hero Slides",
                        "icon": "auto_awesome",
                        "link": lambda request: reverse_lazy("admin:core_heroslide_changelist"),
                    },
                    {
                        "title": "Photos Gallery",
                        "icon": "photo_library",
                        "link": lambda request: reverse_lazy("admin:core_photo_changelist"),
                    },
                    {
                        "title": "Timeline Events",
                        "icon": "timeline",
                        "link": lambda request: reverse_lazy("admin:core_timelineevent_changelist"),
                    },
                    {
                        "title": "Scrapbook Memories",
                        "icon": "auto_stories",
                        "link": lambda request: reverse_lazy("admin:core_scrapbookplacement_changelist"),
                    },
                    {
                        "title": "Video Memories",
                        "icon": "movie",
                        "link": lambda request: reverse_lazy("admin:core_video_changelist"),
                    },
                ],
            },
            {
                "title": "PEOPLE & PROFILES",
                "separator": True,
                "items": [
                    {
                        "title": "Classmate Yearbook",
                        "icon": "groups",
                        "link": lambda request: reverse_lazy("admin:core_student_changelist"),
                    },
                ],
            },
            {
                "title": "SITE PAGES & CONTACT",
                "separator": True,
                "items": [
                    {
                        "title": "About Page",
                        "icon": "info",
                        "link": lambda request: reverse_lazy("admin:core_aboutpage_changelist"),
                    },
                    {
                        "title": "Contact Page",
                        "icon": "contact_support",
                        "link": lambda request: reverse_lazy("admin:core_contactpage_changelist"),
                    },
                    {
                        "title": "Contact Messages",
                        "icon": "mail",
                        "link": lambda request: reverse_lazy("admin:core_contactmessage_changelist"),
                    },
                ],
            },
            {
                "title": "ORGANIZATION",
                "separator": True,
                "items": [
                    {
                        "title": "Categories",
                        "icon": "category",
                        "link": lambda request: reverse_lazy("admin:core_category_changelist"),
                    },
                ],
            },
            {
                "title": "SYSTEM & SECURITY",
                "separator": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": lambda request: reverse_lazy("admin:auth_user_changelist"),
                    },
                    {
                        "title": "Groups",
                        "icon": "manage_accounts",
                        "link": lambda request: reverse_lazy("admin:auth_group_changelist"),
                    },
                ],
            },
        ],
    },
}


# ==============================================================================
# LOGGING
# ==============================================================================

DJANGO_LOG_LEVEL = _get_env(
    "DJANGO_LOG_LEVEL",
    "INFO",
)

LOGGING = {
    "version": 1,

    "disable_existing_loggers": False,

    "formatters": {
        "verbose": {
            "format":
                "{levelname} {asctime} {module} "
                "{process:d} {thread:d} {message}",

            "style": "{",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },

    "root": {
        "handlers": [
            "console",
        ],

        "level": "WARNING",
    },

    "loggers": {
        "django": {
            "handlers": [
                "console",
            ],

            "level": DJANGO_LOG_LEVEL,

            "propagate": False,
        },

        "django.request": {
            "handlers": [
                "console",
            ],

            "level": "ERROR",

            "propagate": False,
        },

        "django.security": {
            "handlers": [
                "console",
            ],

            "level": "WARNING",

            "propagate": False,
        },
    },
}


# ==============================================================================
# EMAIL / SMTP
# ==============================================================================

EMAIL_BACKEND = _get_env(
    "DJANGO_EMAIL_BACKEND",
    (
        "django.core.mail.backends.console.EmailBackend"
        if DEBUG
        else "django.core.mail.backends.smtp.EmailBackend"
    ),
)

EMAIL_HOST = _get_env(
    "EMAIL_HOST",
    "smtp.gmail.com",
)

EMAIL_PORT = _get_int_env(
    "EMAIL_PORT",
    587,
)

EMAIL_HOST_USER = _get_env(
    "EMAIL_HOST_USER",
    "",
)

EMAIL_HOST_PASSWORD = _get_env(
    "EMAIL_HOST_PASSWORD",
    "",
)

EMAIL_USE_TLS = _get_bool_env(
    "EMAIL_USE_TLS",
    True,
)

EMAIL_TIMEOUT = _get_int_env(
    "EMAIL_TIMEOUT",
    10,
)

DEFAULT_FROM_EMAIL = _get_env(
    "DEFAULT_FROM_EMAIL",
    "Echoes Of SMASC <noreply@example.com>",
)

CONTACT_NOTIFICATION_EMAIL = _get_env(
    "CONTACT_NOTIFICATION_EMAIL",
    "admin@example.com",
)


# ==============================================================================
# UPLOAD LIMITS
# ==============================================================================

MAX_IMAGE_UPLOAD_SIZE = _get_int_env(
    "MAX_IMAGE_UPLOAD_SIZE",
    25 * 1024 * 1024,
)

MAX_VIDEO_UPLOAD_SIZE = _get_int_env(
    "MAX_VIDEO_UPLOAD_SIZE",
    500 * 1024 * 1024,
)

DATA_UPLOAD_MAX_MEMORY_SIZE = _get_int_env(
    "DATA_UPLOAD_MAX_MEMORY_SIZE",
    50 * 1024 * 1024,
)

FILE_UPLOAD_MAX_MEMORY_SIZE = _get_int_env(
    "FILE_UPLOAD_MAX_MEMORY_SIZE",
    50 * 1024 * 1024,
)


# ==============================================================================
# PRODUCTION SAFETY CHECKS
# ==============================================================================

if not DEBUG and not IS_TESTING:

    if not DATABASE_URL:
        import warnings

        warnings.warn(
            "DATABASE_URL is not set; falling back to local/persistent SQLite. "
            "Configure DATABASE_URL with a PostgreSQL connection string for production persistence.",
            RuntimeWarning,
        )

    if not USE_S3:
        import warnings

        warnings.warn(
            "USE_S3 is disabled in production. "
            "Uploaded media stored on the Render web-service "
            "filesystem is not guaranteed to persist across "
            "deployments/restarts without a persistent disk mount. "
            "Configure a persistent disk or S3 object storage for production media.",
            RuntimeWarning,
        )