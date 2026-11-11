from rest_framework import serializers

from core.models import Country, Message

from .country import CountrySerializer


class MessageConversationSerializer(CountrySerializer):
    unread_count = serializers.IntegerField(read_only=True)
    last_message_at = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta(CountrySerializer.Meta):
        fields = ['id', 'name', 'political_name', 'flag', 'unread_count', 'last_message_at']


class MessageCountrySerializer(serializers.Serializer):
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all())


class MessageReadSerializer(MessageCountrySerializer):
    last_message_id = serializers.IntegerField(min_value=1)


class MessageSerializer(serializers.ModelSerializer):
    text = serializers.CharField(max_length=2000)
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
