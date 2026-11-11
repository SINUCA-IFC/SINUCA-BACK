from rest_framework import serializers

from uploader.fields import LimitedImageField
from uploader.models import Image


class ImageUploadSerializer(serializers.ModelSerializer):
    file = LimitedImageField(write_only=True)

    class Meta:
        model = Image
        fields = ["id", "attachment_key", "file", "description", "uploaded_on", "url"]
        read_only_fields = ["attachment_key", "uploaded_on", "url"]
        extra_kwargs = {"file": {"write_only": True}}


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ["url", "description", "uploaded_on"]
        read_only_fields = ["url", "attachment_key", "uploaded_on"]

    def create(self, validated_data):
        raise NotImplementedError("Use ImageUploadSerializer to create images.")
