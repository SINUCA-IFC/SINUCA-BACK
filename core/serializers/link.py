from rest_framework.serializers import ModelSerializer

from core.models import Link


class LinkSerializer(ModelSerializer):
    class Meta:
        model = Link
        fields = '__all__'
