from rest_framework.viewsets import ModelViewSet

from core.models import Category
from core.permissions import IsOrganizerOrReadOnly
from core.serializers import CategorySerializer


class CategoryViewSet(ModelViewSet):
    permission_classes = [IsOrganizerOrReadOnly]
    queryset = Category.objects.all().order_by('id')
    serializer_class = CategorySerializer
