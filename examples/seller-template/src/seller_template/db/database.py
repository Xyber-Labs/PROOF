from typing import Any

_DATABASE: dict[str, dict[str, Any]] = {"tasks": {}}


def get_database() -> dict[str, dict[str, Any]]:
    return _DATABASE


def close_database():
    _DATABASE["tasks"] = {}
