from django.conf import settings
from django.db.models import Sum
from rest_framework import serializers
from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle

from uploader.models import Document, Image


def validate_upload_quota(owner, size):
    images = Image.objects.filter(owner=owner)
    documents = Document.objects.filter(owner=owner)
    if images.count() + documents.count() >= settings.UPLOADER_MAX_FILES_PER_USER:
        raise serializers.ValidationError({'file': 'Limite de arquivos por conta atingido.'})
    used = (images.aggregate(total=Sum('size'))['total'] or 0) + (
        documents.aggregate(total=Sum('size'))['total'] or 0
    )
    if used + size > settings.UPLOADER_MAX_BYTES_PER_USER:
        raise serializers.ValidationError({'file': 'Limite de armazenamento por conta atingido.'})


class UploadRateThrottle(UserRateThrottle):
    scope = 'uploads'
    rate = '10/hour'


class RegistrationRateThrottle(SimpleRateThrottle):
    scope = 'registration'
    rate = '30/minute'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': request.META.get('REMOTE_ADDR', '')}
