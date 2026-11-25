from rest_framework import serializers

from uploader.fields import LimitedDocumentField
from uploader.models import Document


class DocumentUploadSerializer(serializers.ModelSerializer):
    file = LimitedDocumentField(write_only=True)

    class Meta:
        model = Document
        fields = ["attachment_key", "file", "description", "uploaded_on"]
        read_only_fields = ["attachment_key", "uploaded_on"]
