from rest_framework import serializers

from uploader.fields import LimitedDocumentField
from uploader.models import Document


class DocumentUploadSerializer(serializers.ModelSerializer):
    file = LimitedDocumentField(write_only=True)

    class Meta:
        model = Document
        fields = ["attachment_key", "file", "description", "uploaded_on"]
        read_only_fields = ["attachment_key", "uploaded_on"]
        extra_kwargs = {"file": {"write_only": True}}


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["url", "description", "uploaded_on", "attachment_key", "public_id"]
        read_only_fields = ["url", "attachment_key", "uploaded_on"]

    def create(self, validated_data):
        raise NotImplementedError("Use DocumentUploadSerializer to create document files.")
