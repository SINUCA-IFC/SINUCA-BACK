from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from core.models import Schedule


class ScheduleSerializer(ModelSerializer):
    def validate(self, attrs):
        countries = attrs.get('country')
        if countries is None:
            countries = self.instance.country.all() if self.instance else []
        docs = attrs.get('docs')
        if docs is None:
            docs = self.instance.docs.all() if self.instance else []
        country_ids = {country.pk for country in countries}
        for document in docs:
            if not country_ids.issubset(set(document.country.values_list('id', flat=True))):
                raise serializers.ValidationError({
                    'docs': 'Os documentos devem estar disponíveis para todas as delegações da atividade.',
                })
        return attrs

    class Meta:
        model = Schedule
        fields = '__all__'
