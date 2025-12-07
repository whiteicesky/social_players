from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import CheckConstraint, F, Q
from django.utils import timezone

User = get_user_model()


class FriendRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend_requests_sent')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend_requests_received')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            CheckConstraint(condition=~Q(from_user=F('to_user')), name='friend_request_not_self'),
        ]

    def __str__(self) -> str:
        return f'{self.from_user} -> {self.to_user} ({self.status})'


class Friendship(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendship_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendship_user2')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            CheckConstraint(condition=Q(user1__lt=F('user2')), name='friendship_ordering'),
            models.UniqueConstraint(fields=['user1', 'user2'], name='unique_friendship_pair'),
        ]

    def save(self, *args, **kwargs):
        if self.user1_id and self.user2_id and self.user1_id > self.user2_id:
            self.user1, self.user2 = self.user2, self.user1
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.user1} <-> {self.user2}'
