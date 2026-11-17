import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0029_pushsubscription'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [migrations.CreateModel(
        name='TaskOverdueNotification',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('deadline', models.DateField()),
            ('sent_at', models.DateTimeField(auto_now_add=True)),
            ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                      related_name='overdue_notifications', to='core.task')),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ],
        options={'constraints': [models.UniqueConstraint(
            fields=('task', 'user', 'deadline'), name='unique_task_user_overdue_deadline',
        )]},
    )]
