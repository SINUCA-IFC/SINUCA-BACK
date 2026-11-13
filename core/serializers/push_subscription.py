from rest_framework import serializers


class PushSubscriptionKeysSerializer(serializers.Serializer):
    p256dh = serializers.CharField(allow_blank=False, trim_whitespace=True)
    auth = serializers.CharField(allow_blank=False, trim_whitespace=True)


class PushSubscriptionSerializer(serializers.Serializer):
    endpoint = serializers.URLField(allow_blank=False)
    keys = PushSubscriptionKeysSerializer()


class PushSubscriptionDeleteSerializer(serializers.Serializer):
    endpoint = serializers.URLField(allow_blank=False)

