from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='topic',
            field=models.CharField(
                choices=[
                    ('cs2', 'CS2'),
                    ('valorant', 'Valorant'),
                    ('apex', 'Apex Legends'),
                    ('dota2', 'Dota 2'),
                    ('other_game', 'Other games'),
                    ('other', 'Other'),
                ],
                default='other',
                max_length=32,
            ),
        ),
    ]
