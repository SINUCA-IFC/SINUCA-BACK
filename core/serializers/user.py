from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, SlugRelatedField

from core.models import Country, User
from uploader.models import Image
from uploader.serializers import ImageSerializer

from .gang import GangSerializer


class UserSerializer(ModelSerializer):
    approval_pending = serializers.SerializerMethodField()

    def get_approval_pending(self, obj) -> bool:
        return obj.is_student and not obj.is_superuser and obj.country_id is None

    foto_attachment_key = SlugRelatedField(
        source='foto',
        queryset=Image.objects.all(),
        slug_field='attachment_key',
        required=False,
        write_only=True,
    )
    foto = ImageSerializer(
        required=False,
        read_only=True
    )
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
            'approval_pending',
        ]

        read_only_fields = [
            'id',
            'is_active',
            'is_staff',
            'is_superuser',
            'last_login',
            'groups',
            'country',
            'role',
        ]
        depth = 1


class PendingUserSerializer(ModelSerializer):
    foto = ImageSerializer(read_only=True)
    gang = GangSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'foto', 'gang', 'matriculation']
        read_only_fields = fields


class UserRegistrationSerializer(ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    approval_pending = serializers.SerializerMethodField()

    def get_approval_pending(self, obj) -> bool:
        return obj.country_id is None

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'password', 'foto', 'gang', 'matriculation', 'country', 'approval_pending']
        read_only_fields = ['id', 'country']

    def create(self, validated_data):
        validated_data['country'] = None
        validated_data['role'] = User.Role.STUDENT
        return User.objects.create_user(**validated_data)


class UserApprovalSerializer(serializers.Serializer):
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all())
