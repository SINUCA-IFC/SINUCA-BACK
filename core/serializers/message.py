from rest_framework import serializers

from core.models import Message


class MessageSerializer(serializers.ModelSerializer):
    is_mine = serializers.SerializerMethodField()
    creator_name = serializers.CharField(source='creator.name', read_only=True)
    from_organization = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'country', 'creator', 'creator_name', 'from_organization',
                  'text', 'created_at', 'is_mine']
        read_only_fields = ['creator', 'created_at']
        extra_kwargs = {'country': {'required': False}}

    def get_is_mine(self, obj):
        return obj.creator_id == self.context['request'].user.id

    def get_from_organization(self, obj):
        return obj.creator is not None and obj.creator.is_organizer

    def validate(self, attrs):
        user = self.context['request'].user
        if user.is_organizer and not attrs.get('country'):
            raise serializers.ValidationError({'country': 'Informe a delegação.'})
        return attrs