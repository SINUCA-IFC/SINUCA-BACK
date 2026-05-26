from rest_framework.serializers import ModelSerializer

from core.models import Task


class TaskListSerializer(ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'category', 'endDate', 'status']
        depth = 1


class TaskDetailSerializer(ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'
        depth = 1


class TaskSerializer(ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'

    def create(self, validated_data):

        user = self.context['request'].user

        task = Task.objects.create(creator=user, **validated_data)
        return task
