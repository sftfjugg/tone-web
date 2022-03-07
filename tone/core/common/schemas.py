class BaseSchema(object):
    unchangeable_fields = []

    def get_param_data(self):
        pass

    def get_body_data(self):
        pass

    def get_update_data(self):
        pass

    def get_delete_data(self):
        pass
