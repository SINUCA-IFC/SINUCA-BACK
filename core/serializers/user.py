from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, SlugRelatedField

from core.models import User
from uploader.models import Image
from uploader.serializers import ImageSerializer


class UserSerializer(ModelSerializer):
    name = serializers.CharField(required=False, allow_blank=False, allow_null=False, max_length=255)
    foto_attachment_key = SlugRelatedField(
        source='foto',
        allow_null=True,
        queryset=Image.objects.all(),
        slug_field='attachment_key',
        required=False,
        write_only=True,
    )
    foto = ImageSerializer(required=False, read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'name',
            'is_active',
            'is_staff',
            'is_superuser',
            'last_login',
            'groups',
            'foto',
            'foto_attachment_key',
            'country',
            'role',
        ]

        read_only_fields = [
            'id',
            'email',
            'is_active',
            'is_staff',
            'is_superuser',
            'last_login',
            'groups',
            'country',
            'role',
        ]
        depth = 1
