"""
Django settings for navybaby project.
"""

from pathlib import Path
import os
import dj_database_url

# === PATHS ===
BASE_DIR = Path(__file__).resolve().parent.parent

# === SECURITY ===
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-se1$v-h&5b*868ok+@x9%6ay!%654k_5+mhmvhjvo)+!p-%n7z"
)
DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "navybaby-v0-4.onrender.com",
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
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
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

# WhiteNoise: fix lỗi admin static và compress ổn định trên Render
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
WHITENOISE_USE_FINDERS = True  # giúp tìm admin static khi collectstatic

# === MEDIA FILES (Cloudinary / Local) ===
CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL")
USE_CLOUDINARY = bool(CLOUDINARY_URL)

if USE_CLOUDINARY:
    # Prod / Render
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
    MEDIA_URL = "/media/"
else:
    # Dev local
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# === DEFAULTS ===
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# === OPTIONAL: add headers & security for Render + WhiteNoise ===
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# === AUTH REDIRECTS ===
LOGIN_URL = "/dang-nhap/"
LOGIN_REDIRECT_URL = "/"
