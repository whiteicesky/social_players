from django.db import migrations, models


OLD_TO_NEW = {
    "other_game": "other_games",
    "other": "non_game",
}


def forwards(apps, schema_editor):
    Post = apps.get_model('posts', 'Post')
    for old, new in OLD_TO_NEW.items():
        Post.objects.filter(topic=old).update(topic=new)


def backwards(apps, schema_editor):
    Post = apps.get_model('posts', 'Post')
    reverse_map = {v: k for k, v in OLD_TO_NEW.items()}
    for new, old in reverse_map.items():
        Post.objects.filter(topic=new).update(topic=old)


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0002_post_topic'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name='post',
            name='topic',
            field=models.CharField(
                choices=[
                    ('cs2', 'CS2'),
                    ('valorant', 'Valorant'),
                    ('apex', 'Apex Legends'),
                    ('dota2', 'Dota 2'),
                    ('minecraft', 'Minecraft'),
                    ('fortnite', 'Fortnite'),
                    ('pubg', 'PUBG'),
                    ('gta5', 'GTA 5'),
                    ('witcher', 'The Witcher'),
                    ('atomic_heart', 'Atomic Heart'),
                    ('other_games', 'Other Games'),
                    ('non_game', 'Non Game Activity'),
                ],
                default='non_game',
                max_length=32,
            ),
        ),
    ]
