import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from friendships.models import FriendRequest, Friendship
from messaging.models import DirectConversation, DirectMessage
from posts.models import Comment, Like, Post


@pytest.mark.django_db
def test_signup_creates_profile(client):
    response = client.post(
        reverse("accounts:signup"),
        {"username": "alice", "password1": "pass12345", "password2": "pass12345"},
        follow=True,
    )
    assert response.status_code == 200
    assert response.context["user"].is_authenticated
    user = response.context["user"]
    user.refresh_from_db()
    assert user.profile.display_name


@pytest.mark.django_db
def test_login_and_logout_flow(create_user, client, password):
    user = create_user("login_user")
    login_response = client.post(
        reverse("accounts:login"), {"username": user.username, "password": password}
    )
    assert login_response.status_code == 302
    assert login_response.url == reverse("posts:feed")

    feed_response = client.get(reverse("posts:feed"))
    assert feed_response.status_code == 200
    assert feed_response.context["user"].is_authenticated

    logout_response = client.post(reverse("accounts:logout"))
    assert logout_response.status_code == 302
    assert reverse("accounts:login") in logout_response.url

    post_logout_feed = client.get(reverse("posts:feed"))
    assert post_logout_feed.status_code == 302
    assert reverse("accounts:login") in post_logout_feed.url


@pytest.mark.django_db
def test_profile_edit(create_user, client, password):
    user = create_user("bob")
    client.force_login(user)
    response = client.post(
        reverse("profiles:edit"),
        {"display_name": "Bobby", "bio": "Gamer"},
        follow=True,
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.profile.display_name == "Bobby"


@pytest.mark.django_db
def test_friend_request_flow(create_user, client, password):
    user1 = create_user("carol")
    user2 = create_user("dave")

    client.force_login(user1)
    send_url = reverse("friendships:send", args=[user2.id])
    client.post(send_url, follow=True)
    fr = FriendRequest.objects.get(from_user=user1, to_user=user2)
    assert fr.status == FriendRequest.STATUS_PENDING

    client.force_login(user2)
    accept_url = reverse("friendships:accept", args=[fr.id])
    client.post(accept_url, follow=True)
    assert Friendship.objects.filter(user1__in=[user1, user2], user2__in=[user1, user2]).exists()

    client.force_login(user1)
    remove_url = reverse("friendships:remove", args=[user2.id])
    client.post(remove_url, follow=True)
    assert Friendship.objects.count() == 0


@pytest.mark.django_db
def test_posts_like_and_comment(create_user, client):
    user1 = create_user("erin")
    user2 = create_user("frank")
    Friendship.objects.create(user1=user1, user2=user2)

    client.force_login(user1)
    client.post(reverse("posts:feed"), {"content": "Hello world", "topic": Post.TOPIC_NON_GAME}, follow=True)
    post = Post.objects.get(author=user1)

    client.force_login(user2)
    like_url = reverse("posts:toggle_like", args=[post.id])
    client.post(like_url, {"next": reverse("posts:feed")})
    assert Like.objects.filter(post=post, user=user2).exists()

    comment_url = reverse("posts:add_comment", args=[post.id])
    client.post(comment_url, {"content": "Nice post!", "next": reverse("posts:feed")})
    assert Comment.objects.filter(post=post, author=user2).exists()


@pytest.mark.django_db
def test_messaging_between_friends(create_user, client):
    user1 = create_user("gwen")
    user2 = create_user("hank")
    Friendship.objects.create(user1=user1, user2=user2)

    client.force_login(user1)
    start_url = reverse("messaging:start", args=[user2.username])
    response = client.post(start_url, follow=True)
    assert response.status_code == 200
    conversation = DirectConversation.objects.first()
    assert conversation is not None

    detail_url = reverse("messaging:detail", args=[conversation.id])
    client.post(detail_url, {"content": "Hey there"})
    assert DirectMessage.objects.filter(conversation=conversation, sender=user1).exists()

    list_response = client.get(reverse("messaging:list"))
    detail_response = client.get(detail_url)
    profile_link = reverse("profiles:detail", args=[user2.username])
    assert profile_link in list_response.content.decode()
    assert profile_link in detail_response.content.decode()


def _start_conversation(client, user1, user2):
    Friendship.objects.create(user1=user1, user2=user2)
    client.force_login(user1)
    start_url = reverse("messaging:start", args=[user2.username])
    client.post(start_url, follow=True)
    conversation = DirectConversation.objects.first()
    assert conversation is not None
    return conversation


def _make_test_image(name="dm.png"):
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDAT\x08\xd7c``\x00\x00"
        b"\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return SimpleUploadedFile(name, png_bytes, content_type="image/png")


@pytest.mark.django_db
def test_direct_message_with_photo(create_user, client, tmp_path):
    user1 = create_user("iris")
    user2 = create_user("jack")
    with override_settings(MEDIA_ROOT=tmp_path):
        conversation = _start_conversation(client, user1, user2)
        detail_url = reverse("messaging:detail", args=[conversation.id])
        message = DirectMessage.objects.create(
            conversation=conversation, sender=user1, content="Look at this", image=_make_test_image()
        )

        response = client.get(detail_url)
        assert response.status_code == 200
        page = response.content.decode()
        assert message.image
        assert message.image.url in page


@pytest.mark.django_db
def test_direct_message_photo_only_shows_photo_label(create_user, client, tmp_path):
    user1 = create_user("kyle")
    user2 = create_user("lena")
    with override_settings(MEDIA_ROOT=tmp_path):
        conversation = _start_conversation(client, user1, user2)
        DirectMessage.objects.create(
            conversation=conversation, sender=user1, content="", image=_make_test_image("photo-only.png")
        )

        list_html = client.get(reverse("messaging:list")).content.decode()
        assert "Last: Photo" in list_html


@pytest.mark.django_db
def test_direct_message_requires_text_or_photo(create_user, client):
    user1 = create_user("maya")
    user2 = create_user("nate")
    conversation = _start_conversation(client, user1, user2)
    detail_url = reverse("messaging:detail", args=[conversation.id])
    response = client.post(detail_url, {"content": ""}, follow=True)
    assert response.status_code == 200
    assert "Message text or photo is required." in response.content.decode()
    assert DirectMessage.objects.count() == 0


@pytest.mark.django_db
def test_cannot_edit_foreign_post(create_user, client):
    owner = create_user("ivan")
    stranger = create_user("jill")
    client.force_login(owner)
    client.post(reverse("posts:feed"), {"content": "Owner post", "topic": Post.TOPIC_NON_GAME})
    post = Post.objects.get(author=owner)

    client.force_login(stranger)
    edit_url = reverse("posts:post_edit", args=[post.id])
    response = client.get(edit_url)
    assert response.status_code == 404
