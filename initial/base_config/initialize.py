from initial.base_config.data import BASE_CONFIG_DATA
from tone.models import BaseConfig


class BaseConfigDataInitialize(object):
    """
    from initial.base_config.initialize import BaseConfigDataInitialize
    BaseConfigDataInitialize().initialize_base_config()
    """
    def initialize_base_config(self):
        self._clear_base_config_data()
        self._add_base_config_data()

    @staticmethod
    def _clear_base_config_data():
        BaseConfig.objects.all(query_scope='all').delete(really_delete=True)

    @staticmethod
    def _add_base_config_data():
        config_obj_list = [
            BaseConfig(
                config_type=item['config_type'],
                config_key=item['config_key'],
                config_value=item['config_value'],
                bind_stage=item.get('bind_stage', ''),
                description=item['description'],
            )
            for item in BASE_CONFIG_DATA
        ]
        BaseConfig.objects.bulk_create(config_obj_list)
