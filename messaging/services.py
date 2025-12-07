from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from friendships.services import are_friends
from .models import DirectConversation, DirectConversationParticipant, DirectMessage

User = get_user_model()


def find_conversation_between(user_a: User, user_b: User):
    return (
        DirectConversation.objects.filter(participants__user=user_a)
        .filter(participants__user=user_b)
        .distinct()
        .first()
    )


@transaction.atomic
def get_or_create_conversation(user_a: User, user_b: User, created_by: User | None = None) -> DirectConversation:
    if user_a == user_b:
        raise ValueError("Cannot start a conversation with yourself.")
    if not are_friends(user_a, user_b):
        raise ValueError("Users must be friends to start a conversation.")

    conversation = find_conversation_between(user_a, user_b)
    if conversation:
        DirectConversationParticipant.objects.filter(conversation=conversation, user__in=[user_a, user_b]).update(
            is_deleted=False
        )
        return conversation

    conversation = DirectConversation.objects.create(created_by=created_by or user_a)
    DirectConversationParticipant.objects.bulk_create(
        [
            DirectConversationParticipant(conversation=conversation, user=user_a),
            DirectConversationParticipant(conversation=conversation, user=user_b),
        ]
    )
    return conversation


def ensure_participant(conversation: DirectConversation, user: User) -> DirectConversationParticipant:
    participation = DirectConversationParticipant.objects.filter(conversation=conversation, user=user).first()
    if not participation:
        raise PermissionError("User is not part of the conversation.")
    if participation.is_deleted:
        participation.is_deleted = False
        participation.save(update_fields=['is_deleted'])
    return participation


@transaction.atomic
def send_message(
    conversation: DirectConversation, sender: User, content: str, image=None
) -> DirectMessage:
    ensure_participant(conversation, sender)
    message = DirectMessage.objects.create(conversation=conversation, sender=sender, content=content, image=image)
    DirectConversationParticipant.objects.filter(conversation=conversation).update(is_deleted=False)
    return message


def get_user_conversations(user: User):
    return DirectConversation.objects.filter(participants__user=user, participants__is_deleted=False).distinct()
