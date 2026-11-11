from rest_framework.serializers import ModelSerializer

from core.models import Country
from uploader.fields import OwnedImageField
from uploader.serializers import ImageSerializer


class CountrySerializer(ModelSerializer):
    flag_attachment_key = OwnedImageField(
        source='flag',
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
