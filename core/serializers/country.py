from rest_framework.serializers import ModelSerializer, SlugRelatedField

from core.models import Country
from uploader.models import Image
from uploader.serializers import ImageSerializer

class CountrySerializer(ModelSerializer):
    flag_attachment_key = SlugRelatedField(
        source='flag',
        queryset=Image.objects.all(),
        slug_field='attachment_key',
        required=False,
        write_only=True,
    )
    flag = ImageSerializer(
        required=False,
        read_only=True
    )

    class Meta:
        model = Country
        fields = ['id', 'name', 'political_name', 'flag', 'flag_attachment_key']
