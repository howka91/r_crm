"""Development settings — DEBUG on, permissive CORS."""
from .base import *  # noqa: F401, F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = ["*"]

# During development allow all origins (frontend at :5173 may change ports).
CORS_ALLOW_ALL_ORIGINS = True

# Toolbar could be added later if needed.
INTERNAL_IPS = ["127.0.0.1"]

# Dev-only logging: verbose for apps.
LOGGING = {  # noqa: F811
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "apps": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
        "django.db.backends": {
            "handlers": ["console"],
            "level": "INFO",  # set to DEBUG to see SQL
            "propagate": False,
        },
    },
}

_ = env  # keep import live
