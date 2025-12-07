import pytest

from friendships import services as friendship_services
from friendships.models import FriendRequest, Friendship
from messaging import services as messaging_services
from messaging.models import DirectConversationParticipant, DirectMessage
from posts import services as post_services
from posts.forms import PostForm
from posts.models import Comment, Like, Post


@pytest.mark.django_db
def test_ordered_pair_rejects_same_user(create_user):
    user = create_user("solo")
    with pytest.raises(ValueError):
        friendship_services._ordered_pair(user, user)


@pytest.mark.django_db
def test_send_and_accept_friend_request(create_user):
    sender = create_user("sender")
    receiver = create_user("receiver")

    friend_request = friendship_services.send_friend_request(sender, receiver)
    assert friend_request.status == FriendRequest.STATUS_PENDING

    friendship = friendship_services.accept_friend_request(friend_request)
    assert friendship.user1_id < friendship.user2_id
    friend_request.refresh_from_db()
    assert friend_request.status == FriendRequest.STATUS_ACCEPTED
    assert friend_request.responded_at is not None


@pytest.mark.django_db
def test_send_friend_request_rejects_duplicates_and_existing_friendship(create_user):
    first = create_user("first")
    second = create_user("second")

    friendship_services.send_friend_request(first, second)
    with pytest.raises(ValueError):
        friendship_services.send_friend_request(first, second)
    with pytest.raises(ValueError):
        friendship_services.send_friend_request(second, first)

    req = FriendRequest.objects.get(from_user=first, to_user=second)
    friendship_services.accept_friend_request(req)
    with pytest.raises(ValueError):
        friendship_services.send_friend_request(first, second)


@pytest.mark.django_db
def test_reject_and_cancel_friend_requests(create_user):
    author = create_user("author")
    target = create_user("target")
    outgoing = FriendRequest.objects.create(from_user=author, to_user=target)
    incoming = FriendRequest.objects.create(from_user=target, to_user=author)

    cancelled = friendship_services.cancel_friend_request(outgoing)
    assert cancelled.status == FriendRequest.STATUS_CANCELLED
    assert cancelled.responded_at is not None

    rejected = friendship_services.reject_friend_request(incoming)
    assert rejected.status == FriendRequest.STATUS_REJECTED
    assert rejected.responded_at is not None

    for fr in (cancelled, rejected):
        with pytest.raises(ValueError):
            friendship_services.cancel_friend_request(fr)
        with pytest.raises(ValueError):
            friendship_services.reject_friend_request(fr)


@pytest.mark.django_db
def test_remove_friendship_returns_deleted_instance(create_user):
    user_a = create_user("alpha")
    user_b = create_user("bravo")
    friendship = Friendship(user1=user_b, user2=user_a)
    friendship.save()

    removed = friendship_services.remove_friendship(user_a, user_b)
    assert removed is not None
    assert Friendship.objects.count() == 0


@pytest.mark.django_db
def test_friend_map_lists_two_way_connections(create_user):
    owner = create_user("owner")
    friend_one = create_user("friend1")
    friend_two = create_user("friend2")
    Friendship.objects.create(user1=owner, user2=friend_one)
    Friendship.objects.create(user1=friend_two, user2=owner)

    mapping = friendship_services.get_friend_map_for_users([owner, friend_one, friend_two])
    assert mapping[owner.id] == {friend_one.id, friend_two.id}
    assert mapping[friend_one.id] == {owner.id}
    assert mapping[friend_two.id] == {owner.id}


@pytest.mark.django_db
def test_get_friendship_respects_ordering(create_user):
    user_a = create_user("ordered_a")
    user_b = create_user("ordered_b")
    friendship = Friendship.objects.create(user1=user_b, user2=user_a)

    fetched = friendship_services.get_friendship(user_a, user_b)
    assert fetched == friendship


@pytest.mark.django_db
def test_toggle_like_and_comment_block_deleted_post(create_user):
    author = create_user("author")
    viewer = create_user("viewer")
    post = Post.objects.create(author=author, content="hidden", topic=Post.TOPIC_NON_GAME, is_deleted=True)

    with pytest.raises(ValueError):
        post_services.toggle_like(post, viewer)
    with pytest.raises(ValueError):
        post_services.add_comment(post, viewer, "Should fail")


@pytest.mark.django_db
def test_mark_likes_for_user_sets_flag(create_user):
    author = create_user("author")
    fan = create_user("fan")
    post = Post.objects.create(author=author, content="likeable", topic=Post.TOPIC_APEX)
    Like.objects.create(post=post, user=fan)

    posts, liked_ids = post_services.mark_likes_for_user([post], fan)
    assert liked_ids == {post.id}
    assert posts[0].liked_by_current_user is True


@pytest.mark.django_db
def test_build_friend_comment_flags_marks_friends(create_user):
    author = create_user("author")
    friend = create_user("friend")
    outsider = create_user("outsider")
    Friendship.objects.create(user1=author, user2=friend)
    post = Post.objects.create(author=author, content="hi", topic=Post.TOPIC_VALORANT)
    friend_comment = Comment.objects.create(post=post, author=friend, content="from friend")
    stranger_comment = Comment.objects.create(post=post, author=outsider, content="from stranger")

    flags, _ = post_services.build_friend_comment_flags([post])
    assert flags[friend_comment.id] is True
    assert flags[stranger_comment.id] is False


def test_post_form_sets_default_topic():
    form = PostForm()
    assert form.fields["topic"].initial == Post.TOPIC_NON_GAME


@pytest.mark.django_db
def test_get_or_create_conversation_validates_friendship(create_user):
    user = create_user("talker")
    stranger = create_user("stranger")
    with pytest.raises(ValueError):
        messaging_services.get_or_create_conversation(user, stranger)
    with pytest.raises(ValueError):
        messaging_services.get_or_create_conversation(user, user)


@pytest.mark.django_db
def test_get_or_create_conversation_revives_deleted_participants(create_user):
    user_a = create_user("user_a")
    user_b = create_user("user_b")
    Friendship.objects.create(user1=user_a, user2=user_b)

    convo = messaging_services.get_or_create_conversation(user_a, user_b, created_by=user_a)
    DirectConversationParticipant.objects.filter(conversation=convo).update(is_deleted=True)

    revived = messaging_services.get_or_create_conversation(user_a, user_b)
    participants = DirectConversationParticipant.objects.filter(conversation=revived)
    assert revived.pk == convo.pk
    assert participants.filter(is_deleted=False).count() == 2


@pytest.mark.django_db
def test_ensure_participant_blocks_unknown_user(create_user):
    user_a = create_user("user_a")
    user_b = create_user("user_b")
    outsider = create_user("outsider")
    Friendship.objects.create(user1=user_a, user2=user_b)
    convo = messaging_services.get_or_create_conversation(user_a, user_b)

    with pytest.raises(PermissionError):
        messaging_services.ensure_participant(convo, outsider)


@pytest.mark.django_db
def test_send_message_resets_deleted_flags(create_user):
    sender = create_user("sender")
    recipient = create_user("recipient")
    Friendship.objects.create(user1=sender, user2=recipient)
    convo = messaging_services.get_or_create_conversation(sender, recipient)
    DirectConversationParticipant.objects.filter(conversation=convo).update(is_deleted=True)

    message = messaging_services.send_message(convo, sender, "Hello again")
    assert isinstance(message, DirectMessage)
    assert DirectConversationParticipant.objects.filter(conversation=convo, is_deleted=False).count() == 2


@pytest.mark.django_db
def test_get_user_conversations_excludes_deleted_participation(create_user):
    owner = create_user("owner")
    buddy = create_user("buddy")
    Friendship.objects.create(user1=owner, user2=buddy)
    convo = messaging_services.get_or_create_conversation(owner, buddy)
    DirectConversationParticipant.objects.filter(conversation=convo, user=owner).update(is_deleted=True)

    assert messaging_services.get_user_conversations(owner).count() == 0
    DirectConversationParticipant.objects.filter(conversation=convo, user=owner).update(is_deleted=False)
    assert messaging_services.get_user_conversations(owner).count() == 1
