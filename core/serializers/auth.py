from rest_framework import serializers

from core.models import User


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'password', 'foto', 'gang', 'matriculation', 'country']


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class VerificationSerializer(serializers.Serializer):
    key = serializers.RegexField(r'^\d{6}$', help_text='Código de seis dígitos, preservando zeros iniciais.')


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class PendingVerificationSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)
    session_token = serializers.CharField(read_only=True)
    email_verification_required = serializers.BooleanField(read_only=True)


class RegistrationResponseSerializer(RegistrationSerializer, PendingVerificationSerializer):
    class Meta(RegistrationSerializer.Meta):
        fields = RegistrationSerializer.Meta.fields + ['detail', 'session_token', 'email_verification_required']
