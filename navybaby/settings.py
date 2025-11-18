"""
Django settings for navybaby project (Render-ready).
Place this file at: <project>/navybaby/settings.py
"""

from pathlib import Path
import os
import dj_database_url

# === PATHS ===
BASE_DIR = Path(__file__).resolve().parent.parent

# === SECURITY / ENV ===
# Use DJANGO_SECRET_KEY environment variable in production.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-se1$v-h&5b*868ok+@x9%6ay!%654k_5+mhmvhjvo)+!p-%n7z"
)

# DEBUG defaults to True locally; set DEBUG=False on Render
DEBUG = os.environ.get("DEBUG", "True") == "True"

# Explicit allowlist including Render domain
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "navybaby.onrender.com",
]

# === APPS ===
INSTALLED_APPS = [
    # Django built-in
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    # Third-party
    "widget_tweaks",
    "cloudinary_storage",
    "cloudinary",

    # Project apps
    "core",
    "accounts",
    "customers",
    "products",
    "orders",
    "categories",
    "suppliers",
    "finance",
]

# === MIDDLEWARE ===
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serve static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.ApprovalRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# === URL / WSGI ===
ROOT_URLCONF = "navybaby.urls"
WSGI_APPLICATION = "navybaby.wsgi.application"

# === TEMPLATES ===
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# === DATABASE ===
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    _db_name = os.environ.get("DB_NAME")
    _db_user = os.environ.get("DB_USER")
    _db_password = os.environ.get("DB_PASSWORD")
    _db_host = os.environ.get("DB_HOST")
    _db_port = os.environ.get("DB_PORT", "5432")
    if all([_db_name, _db_user, _db_password, _db_host]):
        DATABASE_URL = f"postgresql://{_db_user}:{_db_password}@{_db_host}:{_db_port}/{_db_name}"

CONN_MAX_AGE = int(os.environ.get("CONN_MAX_AGE", "600"))

DATABASES = {
    "default": dj_database_url.config(
        default=(DATABASE_URL or f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=CONN_MAX_AGE,
        ssl_require=not DEBUG,
    )
}


# === PASSWORD VALIDATORS ===
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# === AUTHENTICATION ===
AUTH_USER_MODEL = "accounts.User"

# === INTERNATIONALIZATION ===
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

# === STATIC FILES ===
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise: fix lỗi admin static và compress ổn định trên Render
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
WHITENOISE_USE_FINDERS = True  # giúp tìm admin static khi collectstatic

# === MEDIA FILES (Cloudinary or Local) ===
CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL", "")
USE_CLOUDINARY = bool(CLOUDINARY_URL)

if USE_CLOUDINARY:
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
    MEDIA_URL = "/media/"
else:
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# === DEFAULTS ===
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# === SECURITY SETTINGS (Render) ===
# When Render sits behind a proxy/load balancer
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# HSTS (optional, enable after verifying HTTPS works)
if not DEBUG:
    SECURE_HSTS_SECONDS = 60  # increase after verifying (e.g. to 3600 or more)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# === AUTH REDIRECTS ===
LOGIN_URL = "/dang-nhap/"
LOGIN_REDIRECT_URL = "/"

# === LOGGING: helpful for diagnosing 500 errors on Render ===
LOG_LEVEL = "DEBUG" if DEBUG else "INFO"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": True},
        "": {"handlers": ["console"], "level": LOG_LEVEL},
    },
}

# Optional: email admin on errors (configure env vars to enable)
ADMINS = tuple(
    [tuple(a.split(",")) for a in os.environ.get("ADMINS", "").split(";") if a]
)  # format: "name,email;name2,email2"

# Print DB config to logs when DEBUG to aid troubleshooting (not printing secrets)
if DEBUG:
    from pprint import pformat

    try:
        dbinfo = DATABASES.get("default", {})
        print("DATABASE CONFIG:", pformat(dbinfo))
    except Exception:
        pass
