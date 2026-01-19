from logging.config import dictConfig

from xy_market.config import get_app_settings


def get_logging_config() -> dict:
    settings = get_app_settings()
    level = settings.logging_level

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": level,
                "stream": "ext://sys.stdout",
            },
        },
        "root": {"handlers": ["console"], "level": level},
    }


def configure_logging() -> None:
    dictConfig(get_logging_config())
