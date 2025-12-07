from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class DirectConversation(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversations_started'
    )

    def __str__(self) -> str:
        return f'Conversation {self.id}'


class DirectConversationParticipant(models.Model):
    conversation = models.ForeignKey(DirectConversation, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dm_participations')
    is_deleted = models.BooleanField(default=False)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('conversation', 'user')]

    def __str__(self) -> str:
        return f'{self.user} in {self.conversation_id}'


class DirectMessage(models.Model):
    conversation = models.ForeignKey(DirectConversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to='dm_photos/', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_for_sender = models.BooleanField(default=False)
    deleted_for_recipient = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self) -> str:
        return f'Message {self.id} in {self.conversation_id}'
