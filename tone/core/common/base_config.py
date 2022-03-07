import json

from tone.models import BaseConfig


def _serializable(value_type):
    return value_type in [dict, list]


def get_config_from_model(key, value_type=str, default=None):
    config_obj = BaseConfig.objects.filter(config_key=key)
    if not config_obj.exists():
        return default
    if _serializable(value_type):
        return json.loads(config_obj.first().config_value)
    return value_type(config_obj.first().config_value)
