from rest_framework.serializers import ModelSerializer

from core.models import Gang


class GangSerializer(ModelSerializer):
    class Meta:
        model = Gang
        fields = '__all__'
