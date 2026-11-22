from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('core', '0030_taskoverduenotification')]
    operations = [migrations.AddField(model_name='link', name='category', field=models.IntegerField(blank=True, null=True, choices=[(2, 'Debate'), (3, 'Mesa de cooperação')]))]
