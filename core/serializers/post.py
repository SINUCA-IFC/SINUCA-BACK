from rest_framework.serializers import ModelSerializer

from core.models import Post
from uploader.fields import OwnedImageField
from uploader.serializers import ImageSerializer


class PostSerializer(ModelSerializer):

    foto_attachment_key = OwnedImageField(
        source='foto',
        required=False,
        write_only=True,
    )
    foto = ImageSerializer(required=False, read_only=True)

    class Meta:
        model = Post
        fields = '__all__'
