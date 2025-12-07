import pytest

from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from friendships import services as friendship_services
from friendships.models import FriendRequest, Friendship
from messaging import services as messaging_services
from messaging.models import DirectConversation, DirectMessage
from posts.models import Post
from profiles.views import _friend_status


pytestmark = pytest.mark.django_db


def test_signup_redirects_authenticated_user(client, create_user):
    user = create_user("signed")
    client.force_login(user)
    response = client.get(reverse("accounts:signup"))
    assert response.status_code == 302
    assert response.url == reverse("posts:feed")


def test_profile_detail_blocks_foreign_posting(client, create_user):
    owner = create_user("owner")
    intruder = create_user("intruder")
    client.force_login(intruder)
    response = client.post(
        reverse("profiles:detail", args=[owner.username]),
        {"content": "nope", "topic": Post.TOPIC_APEX},
        follow=True,
    )
    assert response.redirect_chain
    assert Post.objects.filter(author=owner).count() == 0


def test_profile_counts_and_status(client, create_user):
    profile_user = create_user("profiled")
    viewer = create_user("viewer")
    friend = create_user("friend")

    pending = FriendRequest.objects.create(from_user=viewer, to_user=profile_user)
    accepted = FriendRequest.objects.create(from_user=friend, to_user=profile_user)
    friendship_services.accept_friend_request(accepted)

    client.force_login(viewer)
    response = client.get(reverse("profiles:detail", args=[profile_user.username]))
    assert response.context["friend_count"] == 1
    assert response.context["follower_count"] == 2
    assert response.context["friend_status"] == "outgoing"
    assert response.context["outgoing_request"] == pending


def test_friend_status_matrix(create_user):
    anon = AnonymousUser()
    self_user = create_user("selfy")
    assert _friend_status(self_user, self_user) == "self"
    assert _friend_status(anon, self_user) == "anonymous"

    user_a = create_user("user_a")
    user_b = create_user("user_b")
    Friendship.objects.create(user1=user_a, user2=user_b)
    assert _friend_status(user_a, user_b) == "friends"

    requester = create_user("requester")
    receiver = create_user("receiver")
    FriendRequest.objects.create(from_user=requester, to_user=receiver)
    assert _friend_status(requester, receiver) == "outgoing"

    target = create_user("target")
    sender = create_user("sender")
    FriendRequest.objects.create(from_user=sender, to_user=target)
    assert _friend_status(target, sender) == "incoming"

    lonely_one = create_user("lonely1")
    lonely_two = create_user("lonely2")
    assert _friend_status(lonely_one, lonely_two) == "none"


@override_settings(MEDIA_ROOT=None)
def test_edit_profile_removes_avatar(tmp_path, client, create_user):
    user = create_user("avatar_user")
    client.force_login(user)
    with override_settings(MEDIA_ROOT=tmp_path):
        profile = user.profile
        profile.avatar.save("avatar.jpg", SimpleUploadedFile("avatar.jpg", b"img", content_type="image/jpeg"))
        profile.save()
        response = client.post(reverse("profiles:edit"), {"remove_avatar": "1"}, follow=True)

    profile.refresh_from_db()
    assert response.status_code == 200
    assert not profile.avatar


def test_friendship_views_list_incoming_and_outgoing(client, create_user):
    user = create_user("owner")
    incoming_user = create_user("incoming")
    outgoing_user = create_user("outgoing")
    friend = create_user("friend")

    FriendRequest.objects.create(from_user=incoming_user, to_user=user)
    FriendRequest.objects.create(from_user=user, to_user=outgoing_user)
    Friendship.objects.create(user1=user, user2=friend)

    client.force_login(user)
    friends_page = client.get(reverse("friendships:list"))
    assert friend.username in friends_page.content.decode()

    incoming_page = client.get(reverse("friendships:incoming"))
    assert incoming_user.username in incoming_page.content.decode()

    outgoing_page = client.get(reverse("friendships:outgoing"))
    assert outgoing_user.username in outgoing_page.content.decode()


def test_reject_and_cancel_views(client, create_user):
    user = create_user("owner")
    sender = create_user("sender")
    target = create_user("target")

    incoming = FriendRequest.objects.create(from_user=sender, to_user=user)
    outgoing = FriendRequest.objects.create(from_user=user, to_user=target)

    client.force_login(user)
    reject_response = client.post(reverse("friendships:reject", args=[incoming.id]), follow=True)
    cancel_response = client.post(reverse("friendships:cancel", args=[outgoing.id]), follow=True)

    incoming.refresh_from_db()
    outgoing.refresh_from_db()
    assert incoming.status == FriendRequest.STATUS_REJECTED
    assert outgoing.status == FriendRequest.STATUS_CANCELLED
    assert reject_response.status_code == 200
    assert cancel_response.status_code == 200


def test_send_request_get_redirects(client, create_user):
    user = create_user("owner")
    target = create_user("target")
    client.force_login(user)

    response = client.get(reverse("friendships:send", args=[target.id]))
    assert response.status_code == 302
    assert response.url == reverse("profiles:detail", args=[target.username])
    assert FriendRequest.objects.count() == 0


def test_accept_view_get_does_not_change_status(client, create_user):
    user = create_user("owner")
    sender = create_user("sender")
    pending = FriendRequest.objects.create(from_user=sender, to_user=user)
    client.force_login(user)

    response = client.get(reverse("friendships:accept", args=[pending.id]))
    pending.refresh_from_db()
    assert pending.status == FriendRequest.STATUS_PENDING
    assert response.status_code == 302
    assert response.url == reverse("friendships:incoming")


def test_topic_posts_invalid_slug_returns_404(client):
    response = client.get(reverse("posts:topic_posts", args=["unknown"]))
    assert response.status_code == 404


def test_feed_invalid_filters_reset_to_all(client, create_user):
    user = create_user("owner")
    friend = create_user("friend")
    other = create_user("other")
    Friendship.objects.create(user1=user, user2=friend)
    Post.objects.create(author=user, content="hello", topic=Post.TOPIC_NON_GAME)
    client.force_login(user)

    response = client.get(reverse("posts:feed"), {"friend": other.id, "topic": "invalid"})
    assert response.context["selected_friend"] == "all"
    assert response.context["selected_topic"] == "all"


def test_messaging_start_requires_friendship(client, create_user):
    user = create_user("owner")
    stranger = create_user("stranger")
    client.force_login(user)

    response = client.post(reverse("messaging:start", args=[stranger.username]), follow=True)
    assert response.redirect_chain
    assert "Users must be friends" in response.content.decode()
    assert DirectConversation.objects.count() == 0


def test_messaging_start_get_redirects(client, create_user):
    user = create_user("owner")
    friend = create_user("friend")
    client.force_login(user)
    response = client.get(reverse("messaging:start", args=[friend.username]))
    assert response.status_code == 302
    assert response.url == reverse("profiles:detail", args=[friend.username])


def test_conversation_detail_excludes_deleted_flags(client, create_user):
    user = create_user("owner")
    friend = create_user("friend")
    request = friendship_services.send_friend_request(user, friend)
    friendship_services.accept_friend_request(request)
    convo = messaging_services.get_or_create_conversation(user, friend)
    dm1 = DirectMessage.objects.create(conversation=convo, sender=user, content="hide", deleted_for_sender=True)
    dm2 = DirectMessage.objects.create(
        conversation=convo, sender=friend, content="hidden too", deleted_for_recipient=True
    )
    dm3 = DirectMessage.objects.create(conversation=convo, sender=friend, content="visible")
    client.force_login(user)
    response = client.get(reverse("messaging:detail", args=[convo.id]))
    body = response.content.decode()
    assert dm3.content in body
    assert dm1.content not in body
    assert dm2.content not in body


def test_search_matches_hyphenated_topic(client, create_user):
    author = create_user("author")
    Post.objects.create(author=author, content="Atomic news", topic=Post.TOPIC_ATOMIC_HEART)
    client.force_login(author)

    response = client.get(reverse("core:search"), {"q": "atomic-heart"})
    text = response.content.decode()
    assert "Atomic news" in text
    assert reverse("profiles:detail", args=[author.username]) in text


def test_search_without_query_returns_empty_results(client, create_user):
    user = create_user("searcher")
    client.force_login(user)
    response = client.get(reverse("core:search"))
    assert response.status_code == 200
    assert response.context["user_results"] == []
    assert response.context["post_results"] == []


def test_template_tags_helpers():
    from core.templatetags.ui_tags import get_item, next_with_anchor

    assert next_with_anchor("http://localhost/feed?page=2#post-1", 10) == "http://localhost/feed?page=2#post-10"
    assert next_with_anchor("", 5) == "#post-5"
    assert get_item({"a": 1}, "a") == 1
    assert get_item(None, "missing") is None
