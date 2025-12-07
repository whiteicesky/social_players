from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import FriendRequest, Friendship

User = get_user_model()


def _ordered_pair(user_a: User, user_b: User):
    if user_a.id == user_b.id:
        raise ValueError("Cannot use the same user in a friendship pair.")
    return (user_a, user_b) if user_a.id < user_b.id else (user_b, user_a)


def are_friends(user_a: User, user_b: User) -> bool:
    u1, u2 = _ordered_pair(user_a, user_b)
    return Friendship.objects.filter(user1=u1, user2=u2).exists()


def get_friendship(user_a: User, user_b: User):
    u1, u2 = _ordered_pair(user_a, user_b)
    return Friendship.objects.filter(user1=u1, user2=u2).first()


def get_friends_queryset(user: User):
    return (
        User.objects.filter(Q(friendship_user1__user2=user) | Q(friendship_user2__user1=user))
        .distinct()
        .order_by('username')
    )


def get_friend_map_for_users(users):
    user_ids = {u.id for u in users if u and u.id}
    if not user_ids:
        return {}
    friendships = Friendship.objects.filter(Q(user1__in=user_ids) | Q(user2__in=user_ids))
    friend_map = {uid: set() for uid in user_ids}
    for friendship in friendships:
        if friendship.user1_id in user_ids:
            friend_map[friendship.user1_id].add(friendship.user2_id)
        if friendship.user2_id in user_ids:
            friend_map[friendship.user2_id].add(friendship.user1_id)
    return friend_map


@transaction.atomic
def send_friend_request(from_user: User, to_user: User) -> FriendRequest:
    if from_user == to_user:
        raise ValueError("Cannot send a friend request to yourself.")

    if are_friends(from_user, to_user):
        raise ValueError("Users are already friends.")

    existing_pending = FriendRequest.objects.filter(
        status=FriendRequest.STATUS_PENDING,
        from_user=from_user,
        to_user=to_user,
    ).first()
    reverse_pending = FriendRequest.objects.filter(
        status=FriendRequest.STATUS_PENDING,
        from_user=to_user,
        to_user=from_user,
    ).first()
    if existing_pending or reverse_pending:
        raise ValueError("A pending friend request already exists between these users.")

    return FriendRequest.objects.create(from_user=from_user, to_user=to_user)


@transaction.atomic
def accept_friend_request(friend_request: FriendRequest) -> Friendship:
    if friend_request.status != FriendRequest.STATUS_PENDING:
        raise ValueError("Friend request is not pending.")
    friendship = Friendship(user1=friend_request.from_user, user2=friend_request.to_user)
    friendship.save()
    friend_request.status = FriendRequest.STATUS_ACCEPTED
    friend_request.responded_at = timezone.now()
    friend_request.save(update_fields=['status', 'responded_at'])
    return friendship


@transaction.atomic
def reject_friend_request(friend_request: FriendRequest):
    if friend_request.status != FriendRequest.STATUS_PENDING:
        raise ValueError("Friend request is not pending.")
    friend_request.status = FriendRequest.STATUS_REJECTED
    friend_request.responded_at = timezone.now()
    friend_request.save(update_fields=['status', 'responded_at'])
    return friend_request


@transaction.atomic
def cancel_friend_request(friend_request: FriendRequest):
    if friend_request.status != FriendRequest.STATUS_PENDING:
        raise ValueError("Friend request is not pending.")
    friend_request.status = FriendRequest.STATUS_CANCELLED
    friend_request.responded_at = timezone.now()
    friend_request.save(update_fields=['status', 'responded_at'])
    return friend_request


@transaction.atomic
def remove_friendship(user_a: User, user_b: User):
    friendship = get_friendship(user_a, user_b)
    if friendship:
        friendship.delete()
    return friendship
