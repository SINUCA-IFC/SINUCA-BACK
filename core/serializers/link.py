from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from core.models import Link


class LinkSerializer(ModelSerializer):

    categories = serializers.SerializerMethodField()

    def validate_country(self, countries):
        if self.instance:
            required = set(self.instance.schedules.values_list('country', flat=True)) - {None}
            if not required.issubset({country.pk for country in countries}):
                raise serializers.ValidationError('Há atividades usando este documento nas delegações removidas.')
        return countries

    class Meta:
        model = Link
        fields = [
            'id',
            'name',
            'url',
            'categories',
            'country',
        ]

    def get_categories(self, obj):
        return list(
            obj.schedules
                .values_list('category', flat=True)
                .distinct()
        )
