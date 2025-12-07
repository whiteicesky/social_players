from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render, resolve_url

from friendships.services import get_friends_queryset
from .forms import CommentForm, PostForm
from .models import Comment, Post
from .services import (
    add_comment,
    build_friend_comment_flags,
    get_all_active_posts,
    get_feed_posts,
    mark_likes_for_user,
    soft_delete_comment,
    soft_delete_post,
    toggle_like,
)


@login_required
def feed(request):
    order = request.GET.get('order', 'new')
    selected_topic = request.GET.get('topic', '')
    selected_friend = request.GET.get('friend', '')
    friends = get_friends_queryset(request.user).select_related('profile')
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, 'Post created.')
            next_url = request.POST.get('next') or 'posts:feed'
            return redirect(resolve_url(next_url))
    else:
        form = PostForm()
    posts_qs = get_feed_posts(request.user)
    valid_topic_slugs = {value for value, _ in Post.TOPIC_CHOICES}
    allowed_friend_ids = {str(f.id) for f in friends} | {str(request.user.id)}
    if selected_friend and selected_friend != 'all':
        if selected_friend in allowed_friend_ids:
            posts_qs = posts_qs.filter(author_id=int(selected_friend))
        else:
            selected_friend = 'all'
    if selected_topic and selected_topic != 'all':
        if selected_topic in valid_topic_slugs:
            posts_qs = posts_qs.filter(topic=selected_topic)
        else:
            selected_topic = 'all'
    if order == 'old':
        posts_qs = posts_qs.order_by('created_at', 'id')
    else:
        order = 'new'
        posts_qs = posts_qs.order_by('-created_at', '-id')
    posts, _ = mark_likes_for_user(posts_qs, request.user)
    comment_friend_flags, _ = build_friend_comment_flags(posts)
    comment_form = CommentForm()
    return render(
        request,
        'posts/feed.html',
        {
            'posts': posts,
            'form': form,
            'comment_form': comment_form,
            'comment_friend_flags': comment_friend_flags,
            'friends': friends,
            'selected_friend': selected_friend or 'all',
            'selected_topic': selected_topic or 'all',
            'selected_order': order,
            'topics': Post.TOPIC_CHOICES,
        },
    )


def social_players(request):
    return render(request, 'posts/social_players.html', {'topic_choices': Post.TOPIC_CHOICES})


def topic_posts(request, slug):
    topics_map = dict(Post.TOPIC_CHOICES)
    if slug not in topics_map:
        raise Http404("Topic not found")
    posts, _ = mark_likes_for_user(get_all_active_posts().filter(topic=slug), request.user)
    comment_friend_flags, _ = build_friend_comment_flags(posts)
    comment_form = CommentForm()
    return render(
        request,
        'posts/topic_posts.html',
        {
            'posts': posts,
            'topic_label': topics_map[slug],
            'comment_form': comment_form,
            'comment_friend_flags': comment_friend_flags,
        },
    )


@login_required
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user, is_deleted=False)
    next_url = resolve_url(request.POST.get('next') or request.GET.get('next') or 'posts:feed')
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Post updated.')
            return redirect(next_url)
    else:
        form = PostForm(instance=post)
    return render(request, 'posts/edit.html', {'form': form, 'next_url': next_url})


@login_required
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user, is_deleted=False)
    if request.method == 'POST':
        soft_delete_post(post)
        messages.info(request, 'Post deleted.')
    next_url = resolve_url(request.POST.get('next') or 'posts:feed')
    return redirect(next_url)


@login_required
def add_comment_view(request, pk):
    post = get_object_or_404(Post, pk=pk, is_deleted=False)
    if request.method == 'POST':
        form = CommentForm(request.POST, request.FILES)
        if form.is_valid():
            add_comment(post, request.user, form.cleaned_data['content'], form.cleaned_data.get('attachment'))
            messages.success(request, 'Comment added.')
    return redirect(resolve_url(request.POST.get('next') or 'posts:feed'))


@login_required
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk, author=request.user, is_deleted=False)
    if request.method == 'POST':
        soft_delete_comment(comment)
        messages.info(request, 'Comment removed.')
    return redirect(resolve_url(request.POST.get('next') or 'posts:feed'))


@login_required
def toggle_like_view(request, pk):
    post = get_object_or_404(Post, pk=pk, is_deleted=False)
    if request.method == 'POST':
        try:
            toggle_like(post, request.user)
        except ValueError as exc:
            messages.error(request, str(exc))
    return redirect(resolve_url(request.POST.get('next') or 'posts:feed'))
