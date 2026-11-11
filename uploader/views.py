from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import mixins, parsers, viewsets
from rest_framework.permissions import IsAuthenticated

from uploader.limits import UploadRateThrottle, validate_upload_quota
from uploader.models import Document, Image
from uploader.serializers import DocumentUploadSerializer, ImageUploadSerializer


class CreateViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.none()
        return self.queryset.filter(owner=self.request.user).order_by('-uploaded_on', '-pk')

    def get_throttles(self):
        return [UploadRateThrottle()] if self.request.method == 'POST' else []

    def perform_create(self, serializer):
        upload = self.queryset.model(**serializer.validated_data)
        try:
            with transaction.atomic():
                owner = get_user_model().objects.select_for_update().get(pk=self.request.user.pk)
                size = upload.file.size
                validate_upload_quota(owner, size)
                upload.owner = owner
                upload.size = size
                upload.save()
        except Exception:
            if upload.file._committed:
                upload.file.delete(save=False)
            raise
        serializer.instance = upload


class DocumentUploadViewSet(CreateViewSet):
    queryset = Document.objects.all() #  pylint: disable=no-member
    serializer_class = DocumentUploadSerializer
    parser_classes = [parsers.FormParser, parsers.MultiPartParser]


class ImageUploadViewSet(CreateViewSet):
    queryset = Image.objects.all() #  pylint: disable=no-member
    serializer_class = ImageUploadSerializer
    parser_classes = [parsers.FormParser, parsers.MultiPartParser]
