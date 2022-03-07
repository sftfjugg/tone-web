from rest_framework import serializers


class CommonSerializer(serializers.ModelSerializer):
    gmt_created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    gmt_modified = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
