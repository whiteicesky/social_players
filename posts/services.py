from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Prefetch, Q

from friendships.services import get_friend_map_for_users, get_friends_queryset
from .models import Comment, Like, Post

User = get_user_model()


def get_feed_posts(user: User):
    friends = get_friends_queryset(user).values_list('id', flat=True)
    return get_post_base_queryset().filter(Q(author=user) | Q(author__in=friends), is_deleted=False)


def get_post_base_queryset():
    return Post.objects.select_related('author', 'author__profile').prefetch_related(
        'likes',
        Prefetch(
            'comments',
            queryset=Comment.objects.filter(is_deleted=False).select_related('author', 'author__profile'),
            to_attr='active_comments_prefetched',
        ),
    )


def get_user_posts(author: User):
    return get_post_base_queryset().filter(author=author, is_deleted=False)


def get_all_active_posts():
    return get_post_base_queryset().filter(is_deleted=False)


def mark_likes_for_user(posts, user: User):
    posts_list = list(posts)
    liked_post_ids = set()
    if posts_list and getattr(user, "is_authenticated", False):
        liked_post_ids = set(
            Like.objects.filter(post__in=posts_list, user=user).values_list('post_id', flat=True)
        )
    for post in posts_list:
        post.liked_by_current_user = post.id in liked_post_ids
    return posts_list, liked_post_ids


@transaction.atomic
def toggle_like(post: Post, user: User) -> bool:
    if post.is_deleted:
        raise ValueError("Cannot like a deleted post.")
    existing = Like.objects.filter(post=post, user=user)
    if existing.exists():
        existing.delete()
        return False
    try:
        Like.objects.create(post=post, user=user)
        return True
    except IntegrityError:
        return True


@transaction.atomic
def add_comment(post: Post, user: User, content: str, attachment=None) -> Comment:
    if post.is_deleted:
        raise ValueError("Cannot comment on a deleted post.")
    return Comment.objects.create(post=post, author=user, content=content, attachment=attachment)


@transaction.atomic
def soft_delete_post(post: Post):
    post.is_deleted = True
    post.save(update_fields=['is_deleted'])
    return post


@transaction.atomic
def soft_delete_comment(comment: Comment):
    comment.is_deleted = True
    comment.save(update_fields=['is_deleted'])
    return comment


def build_friend_comment_flags(posts):
    posts = list(posts)
    friend_map = get_friend_map_for_users([post.author for post in posts])
    comment_flags = {}
    for post in posts:
        author_friend_ids = friend_map.get(post.author_id, set())
        for comment in getattr(post, 'active_comments', []):
            comment_flags[comment.id] = comment.author_id in author_friend_ids
    return comment_flags, friend_map
