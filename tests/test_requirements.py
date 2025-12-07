from datetime import timedelta
from importlib import util
from pathlib import Path

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import override_settings
from social_players import settings as project_settings
from django.urls import reverse
from django.utils import timezone

from friendships.models import Friendship
from posts.models import Comment, Like, Post


def _load_raw_settings():
    settings_path = Path(__file__).resolve().parent.parent / "social_players" / "settings.py"
    spec = util.spec_from_file_location("raw_project_settings", settings_path)
    module = util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_database_points_to_db_sql():
    raw_settings = _load_raw_settings()
    db_name = raw_settings.DATABASES['default']['NAME']
    db_name_str = str(db_name)
    assert db_name_str.endswith('db.sql')
    assert 'db.sqlite3' not in db_name_str


def test_project_uses_moscow_timezone():
    assert settings.TIME_ZONE == 'Europe/Moscow'


@pytest.mark.django_db
def test_test_database_is_isolated_from_dev_db():
    test_name = str(connection.settings_dict['NAME'])
    dev_name = str(_load_raw_settings().DATABASES['default']['NAME'])
    assert test_name != dev_name


def test_db_init_includes_direct_message_schema():
    init_path = Path(settings.BASE_DIR) / "db_init.sql"
    assert init_path.exists()
    content = init_path.read_text(encoding="utf-8")
    assert 'CREATE TABLE "messaging_directmessage"' in content
    assert '"image"' in content


@pytest.mark.django_db
def test_non_friend_can_comment_and_anonymous_redirects(create_user, client):
    author = create_user("author")
    commenter = create_user("visitor")
    post = Post.objects.create(author=author, content="Hello", topic=Post.TOPIC_NON_GAME)
    url = reverse("posts:add_comment", args=[post.id])

    response = client.post(url, {"content": "No auth"})
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url
    assert Comment.objects.count() == 0

    client.force_login(commenter)
    client.post(url, {"content": "I can comment now"})
    assert Comment.objects.filter(post=post, author=commenter, content="I can comment now").exists()


@pytest.mark.django_db
def test_friend_comment_has_badge(create_user, client):
    author = create_user("author")
    friend = create_user("buddy")
    stranger = create_user("stranger")
    Friendship.objects.create(user1=author, user2=friend)
    post = Post.objects.create(author=author, content="Author post", topic=Post.TOPIC_CS2)
    Comment.objects.create(post=post, author=friend, content="Hi friend")
    Comment.objects.create(post=post, author=stranger, content="Hi stranger")

    client.force_login(author)
    response = client.get(reverse("posts:feed"))
    body = response.content
    assert b"Your Friend" in body
    assert body.count(b'pill-muted">Your Friend') == 1
    assert b"Hi friend" in body
    assert b"Hi stranger" in body


@pytest.mark.django_db
def test_social_players_topics_page_lists_topics_only(create_user, client):
    user = create_user("poster")
    Post.objects.create(author=user, content="CS2 news", topic=Post.TOPIC_CS2)
    Post.objects.create(author=user, content="Valorant tips", topic=Post.TOPIC_VALORANT)
    Post.objects.create(author=user, content="Misc content", topic=Post.TOPIC_OTHER_GAMES)

    response = client.get(reverse("posts:social_players"))
    text = response.content.decode()
    assert "CS2" in text and "Valorant" in text and "Other Games" in text
    assert "CS2 news" not in text
    assert "Valorant tips" not in text
    assert "Misc content" not in text


@pytest.mark.django_db
def test_topic_page_filters_posts(create_user, client):
    user = create_user("poster")
    cs_post = Post.objects.create(author=user, content="CS2 news", topic=Post.TOPIC_CS2)
    Post.objects.create(author=user, content="Valorant tips", topic=Post.TOPIC_VALORANT)
    Post.objects.create(author=user, content="Deleted CS2", topic=Post.TOPIC_CS2, is_deleted=True)

    response = client.get(reverse("posts:topic_posts", args=[Post.TOPIC_CS2]))
    text = response.content.decode()
    assert cs_post.content in text
    assert "Valorant tips" not in text
    assert "Deleted CS2" not in text


@pytest.mark.django_db
def test_home_feed_user_and_friends_sorted(create_user, client):
    user = create_user("owner")
    friend = create_user("ally")
    stranger = create_user("outsider")
    Friendship.objects.create(user1=user, user2=friend)

    older = Post.objects.create(author=user, content="My post", topic=Post.TOPIC_NON_GAME)
    newer = Post.objects.create(author=friend, content="Friend post", topic=Post.TOPIC_VALORANT)
    older.created_at = timezone.now() - timedelta(minutes=5)
    older.save(update_fields=["created_at"])
    Post.objects.create(author=stranger, content="Hidden post", topic=Post.TOPIC_APEX)
    Post.objects.create(author=friend, content="Deleted friend post", topic=Post.TOPIC_CS2, is_deleted=True)

    client.force_login(user)
    response = client.get(reverse("posts:feed"))
    text = response.content.decode()
    assert "Friend post" in text
    assert "My post" in text
    assert "Hidden post" not in text
    assert "Deleted friend post" not in text
    assert text.index("Friend post") < text.index("My post")


@pytest.mark.django_db
def test_feed_filters_and_ordering(create_user, client):
    user = create_user("owner")
    friend = create_user("ally")
    other_friend = create_user("buddy")
    Friendship.objects.create(user1=user, user2=friend)
    Friendship.objects.create(user1=user, user2=other_friend)

    my_post = Post.objects.create(author=user, content="Owner post", topic=Post.TOPIC_APEX)
    friend_post = Post.objects.create(author=friend, content="Friend post", topic=Post.TOPIC_VALORANT)
    friend_post.created_at = timezone.now() - timedelta(minutes=10)
    friend_post.save(update_fields=["created_at"])
    older_friend_post = Post.objects.create(author=other_friend, content="Old friend", topic=Post.TOPIC_VALORANT)
    older_friend_post.created_at = timezone.now() - timedelta(hours=1)
    older_friend_post.save(update_fields=["created_at"])

    client.force_login(user)
    feed_url = reverse("posts:feed")

    friend_filtered = client.get(feed_url, {"friend": friend.id}).content.decode()
    assert "Friend post" in friend_filtered
    assert "Owner post" not in friend_filtered
    assert "Old friend" not in friend_filtered

    topic_filtered = client.get(feed_url, {"topic": Post.TOPIC_VALORANT}).content.decode()
    assert "Friend post" in topic_filtered
    assert "Old friend" in topic_filtered
    assert "Owner post" not in topic_filtered

    asc_order = client.get(feed_url, {"order": "old"}).content.decode()
    assert asc_order.index("Old friend") < asc_order.index("Friend post")
    assert asc_order.index("Friend post") < asc_order.index("Owner post")


@pytest.mark.django_db
def test_profile_owner_can_manage_posts(create_user, client):
    user = create_user("owner")
    profile_url = reverse("profiles:detail", args=[user.username])
    client.force_login(user)

    client.post(profile_url, {"content": "From profile", "topic": Post.TOPIC_APEX}, follow=True)
    post = Post.objects.get(author=user, content="From profile")

    edit_url = reverse("posts:post_edit", args=[post.id]) + f"?next={profile_url}"
    client.post(edit_url, {"content": "Updated content", "topic": Post.TOPIC_APEX}, follow=True)
    post.refresh_from_db()
    assert post.content == "Updated content"

    delete_url = reverse("posts:post_delete", args=[post.id])
    client.post(delete_url, {"next": profile_url}, follow=True)
    post.refresh_from_db()
    assert post.is_deleted is True


@pytest.mark.django_db
def test_like_button_state_and_anchor_redirect(create_user, client):
    author = create_user("author")
    fan = create_user("fan")
    Friendship.objects.create(user1=author, user2=fan)
    post = Post.objects.create(author=author, content="Like me", topic=Post.TOPIC_CS2)

    client.force_login(fan)
    feed_url = reverse("posts:feed")
    like_url = reverse("posts:toggle_like", args=[post.id])
    next_url = f"{feed_url}#post-{post.id}"

    html_before = client.get(feed_url).content.decode()
    assert "like-btn muted" in html_before

    response = client.post(like_url, {"next": next_url})
    assert response.status_code == 302
    assert response.url.endswith(f"#post-{post.id}")
    assert Like.objects.filter(post=post, user=fan).exists()

    html = client.get(feed_url).content.decode()
    assert "like-btn liked" in html


@pytest.mark.django_db
def test_comment_redirect_keeps_anchor(create_user, client):
    author = create_user("author")
    post = Post.objects.create(author=author, content="Comment me", topic=Post.TOPIC_DOTA2)
    client.force_login(author)
    comment_url = reverse("posts:add_comment", args=[post.id])
    next_url = f"{reverse('posts:feed')}#post-{post.id}"

    response = client.post(comment_url, {"content": "Nice", "next": next_url})
    assert response.status_code == 302
    assert response.url.endswith(f"#post-{post.id}")
    comment = Comment.objects.get(post=post, author=author, content="Nice")

    delete_url = reverse("posts:delete_comment", args=[comment.id])
    delete_response = client.post(delete_url, {"next": next_url})
    assert delete_response.status_code == 302
    assert delete_response.url.endswith(f"#post-{post.id}")
    comment.refresh_from_db()
    assert comment.is_deleted is True


@pytest.mark.django_db
def test_comment_with_attachment(create_user, client, tmp_path):
    author = create_user("author")
    commenter = create_user("commenter")
    post = Post.objects.create(author=author, content="Attachment test", topic=Post.TOPIC_NON_GAME)
    comment_url = reverse("posts:add_comment", args=[post.id])
    client.force_login(commenter)

    with override_settings(MEDIA_ROOT=tmp_path):
        file = SimpleUploadedFile("note.txt", b"hello world", content_type="text/plain")
        client.post(comment_url, {"content": "See file", "attachment": file, "next": reverse("posts:feed")}, follow=True)

    comment = Comment.objects.get(post=post, author=commenter)
    assert comment.attachment.name.endswith("note.txt")
    page = client.get(reverse("profiles:detail", args=[author.username])).content.decode()
    assert "View attachment" in page


@pytest.mark.django_db
def test_profile_links_clickable_in_feed(create_user, client):
    author = create_user("author")
    commenter = create_user("guest")
    post = Post.objects.create(author=author, content="Profile links", topic=Post.TOPIC_MINECRAFT)
    Comment.objects.create(post=post, author=commenter, content="Looks good")

    client.force_login(author)
    html = client.get(reverse("posts:feed")).content.decode()
    assert f'href="{reverse("profiles:detail", args=[author.username])}' in html
    assert f'href="{reverse("profiles:detail", args=[commenter.username])}' in html


@pytest.mark.django_db
def test_home_and_profile_headings(create_user, client):
    user = create_user("owner")
    client.force_login(user)

    feed_text = client.get(reverse("posts:feed")).content.decode()
    assert "What's new?" in feed_text
    assert "News From Your Friends" in feed_text

    profile_text = client.get(reverse("profiles:detail", args=[user.username])).content.decode()
    assert "What's new?" in profile_text
    assert "Posts" in profile_text
    assert profile_text.index("What's new?") < profile_text.index("Posts")


@pytest.mark.django_db
def test_topic_search_returns_topic_posts(create_user, client):
    author = create_user("author")
    other = create_user("other")
    target_post = Post.objects.create(author=author, content="Chill update", topic=Post.TOPIC_ATOMIC_HEART)
    Post.objects.create(author=other, content="Building blocks", topic=Post.TOPIC_MINECRAFT)
    client.force_login(author)

    response = client.get(reverse("core:search"), {"q": "Atomic"})
    text = response.content.decode()
    assert target_post.content in text
    assert "Building blocks" not in text
    assert reverse("profiles:detail", args=[author.username]) in text


@pytest.mark.django_db
def test_friends_list_includes_both_sides(create_user, client):
    user = create_user("john")
    friend = create_user("kate")
    Friendship.objects.create(user1=friend, user2=user)

    client.force_login(user)
    response = client.get(reverse("friendships:list"))
    assert response.status_code == 200
    text = response.content.decode()
    assert friend.username in text
    assert f'href="{reverse("profiles:detail", args=[friend.username])}' in text
