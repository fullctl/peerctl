import os

import netom
from fullctl.django import settings

SERVICE_TAG = "peerctl"

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# Intialize settings manager with global variable
settings_manager = settings.SettingsManager(globals())
settings_manager.set_release_env()

# look for mainsite/settings/${RELEASE_ENV}.py and load if it exists
env_file = os.path.join(os.path.dirname(__file__), f"{RELEASE_ENV}.py")
settings_manager.try_include(env_file)


# set version, default from /srv/service/etc/VERSION
settings_manager.set_option(
    "PACKAGE_VERSION", settings.read_file(os.path.join(BASE_DIR, "etc/VERSION")).strip()
)

settings_manager.set_default_v1()

# PEERCTL Base

MIDDLEWARE += (
    # in fullctl    "fullctl.django.middleware.CurrentRequestContext",
    "fullctl.django.middleware.RequestAugmentation",
)

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

settings_manager.set_twentyc_service()

SOCIAL_AUTH_PIPELINE += ("django_peerctl.social.pipelines.create_devices",)

# allow propagation of user field changes during oauth process
# with exception of id fields

SOCIAL_AUTH_NO_DEFAULT_PROTECTED_USER_FIELDS = True

SOCIAL_AUTH_PROTECTED_USER_FIELDS = ("id", "pk")

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


# OUTSIDE SERVICES

settings_manager.set_option("GOOGLE_ANALYTICS_ID", "")

# PEERCTL

# netom integration (templating)

settings_manager.set_option("NETOM_DIR", os.path.dirname(netom.__file__))
settings_manager.set_option(
    "NETOM_TEMPLATE_DIR", os.path.join(NETOM_DIR, "templates", "netom0")
)

# FINALIZE
settings_manager.set_default_append()

# look for mainsite/settings/${RELEASE_ENV}_append.py and load if it exists
env_file = os.path.join(os.path.dirname(__file__), f"{RELEASE_ENV}_append.py")
settings_manager.try_include(env_file)

# TODO combine to log summarry to INFO
settings.print_debug(f"loaded settings for version {PACKAGE_VERSION} (DEBUG: {DEBUG})")
