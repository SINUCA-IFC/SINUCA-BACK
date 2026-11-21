from django.conf import settings
from rest_framework import serializers

from uploader.helpers.files import CONTENT_TYPE_PDF, get_content_type
from uploader.models import Image


class LimitedImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if getattr(data, 'size', 0) > settings.UPLOADER_MAX_IMAGE_BYTES:
            raise serializers.ValidationError('A imagem deve ter no máximo 5 MiB.')
        image = super().to_internal_value(data)
        if image.image.format not in ['JPEG', 'PNG']:
            raise serializers.ValidationError('Envie uma imagem JPEG ou PNG.')
        if max(image.image.size) > settings.UPLOADER_MAX_IMAGE_DIMENSION:
            raise serializers.ValidationError('A imagem deve ter no máximo 4096 pixels por lado.')
        return image


class LimitedDocumentField(serializers.FileField):
    def to_internal_value(self, data):
        file = super().to_internal_value(data)
        if file.size > settings.UPLOADER_MAX_DOCUMENT_BYTES:
            raise serializers.ValidationError('O PDF deve ter no máximo 10 MiB.')
        if get_content_type(file) != CONTENT_TYPE_PDF:
            raise serializers.ValidationError('Envie um arquivo PDF válido.')
        return file


class OwnedImageField(serializers.SlugRelatedField):
    def __init__(self, **kwargs):
        super().__init__(queryset=Image.objects.all(), slug_field='attachment_key', **kwargs)

    def get_queryset(self):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return Image.objects.none()
        return Image.objects.filter(owner=request.user)
