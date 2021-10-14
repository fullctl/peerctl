import os

from confu.util import SettingsManager

_DEFAULT_ARG = object()


def print_debug(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


def get_locale_name(code):
    """Gets the readble name for a locale code."""
    language_map = dict(django.conf.global_settings.LANGUAGES)

    # check for exact match
    if code in language_map:
        return language_map[code]

    # try for the language, fall back to just using the code
    language = code.split("-")[0]
    return language_map.get(language, code)


def try_include(filename):
    """Tries to include another file from the settings directory."""
    print_debug(f"including {filename} {RELEASE_ENV}")
    try:
        with open(filename) as f:
            exec(compile(f.read(), filename, "exec"), globals())

        print_debug(f"loaded additional settings file '{filename}'")

    except FileNotFoundError:
        print_debug(f"additional settings file '{filename}' was not found, skipping")
        pass


def read_file(name):
    with open(name) as fh:
        return fh.read()


# Intialize settings manager with global variable

settings_manager = SettingsManager(globals())


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# set RELEASE_ENV, usually one of dev, beta, tutor, prod
settings_manager.set_option("RELEASE_ENV", "dev")

if RELEASE_ENV in ("dev", "run_tests"):
    settings_manager.set_bool("DEBUG", True)
else:
    settings_manager.set_bool("DEBUG", False)

# look for mainsite/settings/${RELEASE_ENV}.py and load if it exists
env_file = os.path.join(os.path.dirname(__file__), f"{RELEASE_ENV}.py")
try_include(env_file)


print_debug(f"Release env is '{RELEASE_ENV}'")

settings_manager.set_option(
    "PACKAGE_VERSION", read_file(os.path.join(BASE_DIR, "etc/VERSION")).strip()
)

# Contact email, from address, support email
settings_manager.set_from_env("SERVER_EMAIL")

# django secret key
settings_manager.set_from_env("SECRET_KEY")

# database
settings_manager.set_option("DATABASE_ENGINE", "postgresql_psycopg2")

settings_manager.set_from_env("DATABASE_HOST", "")
settings_manager.set_from_env("DATABASE_PORT", "")
settings_manager.set_from_env("DATABASE_NAME", "peerctl")
settings_manager.set_from_env("DATABASE_USER", "peerctl")
settings_manager.set_from_env("DATABASE_PASSWORD", "")


# Django config
ALLOWED_HOSTS = ["*"]
SITE_ID = 1

TIME_ZONE = "UTC"
USE_TZ = True

LANGUAGE_CODE = "en-us"
USE_I18N = True
USE_L10N = True

ADMINS = [("Support", SERVER_EMAIL)]
MANAGERS = ADMINS

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

settings_manager.set_option("HOST_URL", "https://localhost:8000")

settings_manager.set_option(
    "MEDIA_ROOT", os.path.abspath(os.path.join(BASE_DIR, "media"))
)
settings_manager.set_option("MEDIA_URL", f"/m/{PACKAGE_VERSION}/")

settings_manager.set_option(
    "STATIC_ROOT", os.path.abspath(os.path.join(BASE_DIR, "static"))
)
settings_manager.set_option("STATIC_URL", f"/s/{PACKAGE_VERSION}/")

settings_manager.set_option("SESSION_COOKIE_NAME", "peerctlsid")

settings_manager.set_option("DEFAULT_FROM_EMAIL", SERVER_EMAIL)

AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

settings_manager.set_default("MIDDLEWARE", [])
MIDDLEWARE += [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "peerctl.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "peerctl.wsgi.application"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
        "OPTIONS": {
            # maximum number of entries in the cache
            "MAX_ENTRIES": 5000,
            # once max entries are reach delete 500 of the oldest entries
            "CULL_FREQUENCY": 10,
        },
    }
}

DATABASES = {
    "default": {
        "ENGINE": f"django.db.backends.{DATABASE_ENGINE}",
        "HOST": DATABASE_HOST,
        "PORT": DATABASE_PORT,
        "NAME": DATABASE_NAME,
        "USER": DATABASE_USER,
        "PASSWORD": DATABASE_PASSWORD,
    }
}


# start concat config
# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        )
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# PEERCTL Base

MIDDLEWARE += (
    "fullctl.django.middleware.CurrentRequestContext",
    "fullctl.django.middleware.RequestAugmentation",)

INSTALLED_APPS += (
    "dal",
    "dal_select2",
    "django_handleref",
    "django_peeringdb",
    "django_grainy",
    "rest_framework",
    "social_django",
    "reversion",
    "fullctl.django.apps.DjangoFullctlConfig",
    "django_peerctl.apps.DjangoPeerctlConfig",
)

TEMPLATES[0]["OPTIONS"]["context_processors"] += [
    "social_django.context_processors.backends",
    "social_django.context_processors.login_redirect",
    "fullctl.django.context_processors.account_service",
    "fullctl.django.context_processors.permissions",
    "fullctl.django.context_processors.conf",
]

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login"
LOGIN_URL = "/login"

# SERVICE BRIDGES

settings_manager.set_option("PDBCTL_HOST", "")
settings_manager.set_option("IXCTL_HOST", "")

# OAUTH

# 20C

settings_manager.set_option("OAUTH_TWENTYC_HOST", "https://account.20c.com")
OAUTH_TWENTYC_ACCESS_TOKEN_URL = f"{OAUTH_TWENTYC_HOST}/account/auth/o/token/"
OAUTH_TWENTYC_AUTHORIZE_URL = f"{OAUTH_TWENTYC_HOST}/account/auth/o/authorize/"
OAUTH_TWENTYC_PROFILE_URL = f"{OAUTH_TWENTYC_HOST}/account/auth/o/profile/"

settings_manager.set_option("OAUTH_TWENTYC_KEY", "")
settings_manager.set_option("OAUTH_TWENTYC_SECRET", "")

SOCIAL_AUTH_TWENTYC_KEY = OAUTH_TWENTYC_KEY
SOCIAL_AUTH_TWENTYC_SECRET = OAUTH_TWENTYC_SECRET
AUTHENTICATION_BACKENDS = [
    "fullctl.django.social.backends.twentyc.TwentycOAuth2",
] + AUTHENTICATION_BACKENDS

GRAINY_REMOTE = {
    "url_load": f"{OAUTH_TWENTYC_HOST}/grainy/load/",
    # "url_get": f"{OAUTH_TWENTYC_HOST}/grainy/get/" + "{}/",
}

settings_manager.set_option("SOCIAL_AUTH_REDIRECT_IS_HTTPS", True)

SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "fullctl.django.social.pipelines.sync_organizations",
    "social_core.pipeline.user.user_details",
    "django_peerctl.social.pipelines.create_devices",
)

# allow propagation of user field changes during oauth process
# with exception of id fields

SOCIAL_AUTH_NO_DEFAULT_PROTECTED_USER_FIELDS = True

SOCIAL_AUTH_PROTECTED_USER_FIELDS = ("id", "pk")

SERVICE_TAG = "peerctl"

settings_manager.set_option("SERVICE_KEY", "")

# toggle billing integration with aaactl
# if false, billing checks on api end points will be disabled

settings_manager.set_bool("BILLING_INTEGRATION", True)

# PEERINGDB

TABLE_PREFIX = "peeringdb_"
ABSTRACT_ONLY = False

settings_manager.set_option("PDB_API_USERNAME", "")
settings_manager.set_option("PDB_API_PASSWORD", "")

# add user defined iso code for Kosovo
COUNTRIES_OVERRIDE = {
    "XK": "Kosovo",
}

# DJANGO REST FRAMEWORK

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ("fullctl.django.rest.renderers.JSONRenderer",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "fullctl.django.rest.authentication.APIKeyAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    # Use hyperlinked styles by default.
    # Only used if the `serializer_class` attribute is not set on a view.
    "DEFAULT_MODEL_SERIALIZER_CLASS": (
        "rest_framework.serializers.HyperlinkedModelSerializer"
    ),
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    # Handle rest of permissioning via django-namespace-perms
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # FIXME: need to somehow allow different drf settings by app
    "EXCEPTION_HANDLER": "fullctl.django.rest.core.exception_handler",
    "DEFAULT_THROTTLE_RATES": {"email": "1/minute"},
    "DEFAULT_SCHEMA_CLASS": "fullctl.django.rest.api_schema.BaseSchema",
}


# SERVICE BRIDGES

AAACTL_HOST = OAUTH_TWENTYC_HOST

# OUTSIDE SERVICES

settings_manager.set_option("GOOGLE_ANALYTICS_ID", "")

# PEERCTL

# netom integration (templating)

import netom

settings_manager.set_option("NETOM_DIR", os.path.dirname(netom.__file__))
settings_manager.set_option(
    "NETOM_TEMPLATE_DIR", os.path.join(NETOM_DIR, "templates", "netom0")
)

# FINALIZE


DEBUG_EMAIL = DEBUG

TEMPLATES[0]["OPTIONS"]["debug"] = DEBUG

print_debug(f"loaded settings for version {PACKAGE_VERSION} (DEBUG: {DEBUG})")
