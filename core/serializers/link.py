from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from core.models import Link


class LinkSerializer(ModelSerializer):

    categories = serializers.SerializerMethodField()

    class Meta:
        model = Link
        fields = [
            'id',
            'name',
            'url',
            'categories',
        ]

    def get_categories(self, obj):
        return list(
            obj.schedules
                .values_list('category', flat=True)
                .distinct()
        )
