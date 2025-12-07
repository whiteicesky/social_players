from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class Post(models.Model):
    TOPIC_CS2 = 'cs2'
    TOPIC_VALORANT = 'valorant'
    TOPIC_APEX = 'apex'
    TOPIC_DOTA2 = 'dota2'
    TOPIC_MINECRAFT = 'minecraft'
    TOPIC_FORTNITE = 'fortnite'
    TOPIC_PUBG = 'pubg'
    TOPIC_GTA5 = 'gta5'
    TOPIC_WITCHER = 'witcher'
    TOPIC_ATOMIC_HEART = 'atomic_heart'
    TOPIC_OTHER_GAMES = 'other_games'
    TOPIC_NON_GAME = 'non_game'
    TOPIC_OTHER_GAME = TOPIC_OTHER_GAMES  # backward compatibility alias
    TOPIC_OTHER = TOPIC_NON_GAME
    TOPIC_CHOICES = [
        (TOPIC_CS2, 'CS2'),
        (TOPIC_VALORANT, 'Valorant'),
        (TOPIC_APEX, 'Apex Legends'),
        (TOPIC_DOTA2, 'Dota 2'),
        (TOPIC_MINECRAFT, 'Minecraft'),
        (TOPIC_FORTNITE, 'Fortnite'),
        (TOPIC_PUBG, 'PUBG'),
        (TOPIC_GTA5, 'GTA 5'),
        (TOPIC_WITCHER, 'The Witcher'),
        (TOPIC_ATOMIC_HEART, 'Atomic Heart'),
        (TOPIC_OTHER_GAMES, 'Other Games'),
        (TOPIC_NON_GAME, 'Non Game Activity'),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    image = models.ImageField(upload_to='posts/', blank=True, null=True)
    topic = models.CharField(max_length=32, choices=TOPIC_CHOICES, default=TOPIC_NON_GAME)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Post by {self.author}: {self.content[:30]}'

    @property
    def active_comments(self):
        return getattr(self, 'active_comments_prefetched', self.comments.filter(is_deleted=False))

    @property
    def like_count(self):
        prefetched = getattr(self, '_prefetched_objects_cache', {})
        if prefetched and 'likes' in prefetched:
            return len(prefetched['likes'])
        return self.likes.count()


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    attachment = models.FileField(upload_to='comment_attachments/', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self) -> str:
        return f'Comment by {self.author} on {self.post_id}'


class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [('post', 'user')]

    def __str__(self) -> str:
        return f'{self.user} likes {self.post_id}'
