from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from core.models import Task, User
from uploader.serializers import ImageSerializer


class TaskUserSerializer(ModelSerializer):
    foto = ImageSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'foto']


class TaskListSerializer(ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'category', 'endDate', 'status']
        depth = 1


class TaskDetailSerializer(ModelSerializer):
    creator = TaskUserSerializer(read_only=True)
    user = TaskUserSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = '__all__'
        depth = 1


class TaskSerializer(ModelSerializer):
    def to_representation(self, instance):
        return TaskDetailSerializer(instance, context=self.context).data

    def validate_user(self, users):
        request = self.context.get('request')
        actor = getattr(request, 'user', None)
        if actor is None or not actor.is_authenticated:
            raise serializers.ValidationError('É necessário autenticar-se para atribuir responsáveis.')

        if not actor.is_superuser and users and (
            actor.country_id is None or any(user.country_id != actor.country_id for user in users)
        ):
            raise serializers.ValidationError('Os responsáveis devem pertencer à sua delegação.')

        return users

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['creator']
