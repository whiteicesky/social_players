from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from friendships.models import FriendRequest, Friendship
from friendships.services import are_friends
from posts.forms import CommentForm, PostForm
from posts.services import build_friend_comment_flags, get_user_posts, mark_likes_for_user
from .forms import ProfileForm

User = get_user_model()


def _friend_status(current_user, profile_user):
    if not current_user.is_authenticated or current_user == profile_user:
        return 'self' if current_user == profile_user else 'anonymous'
    if are_friends(current_user, profile_user):
        return 'friends'
    if FriendRequest.objects.filter(from_user=current_user, to_user=profile_user, status=FriendRequest.STATUS_PENDING).exists():
        return 'outgoing'
    if FriendRequest.objects.filter(from_user=profile_user, to_user=current_user, status=FriendRequest.STATUS_PENDING).exists():
        return 'incoming'
    return 'none'


def profile_detail(request, username):
    profile_user = get_object_or_404(User, username=username)
    profile = profile_user.profile
    posts, _ = mark_likes_for_user(get_user_posts(profile_user), request.user)
    comment_friend_flags, _ = build_friend_comment_flags(posts)
    comment_form = CommentForm()
    post_form = None
    if request.user.is_authenticated and request.user == profile_user:
        if request.method == 'POST':
            post_form = PostForm(request.POST, request.FILES)
            if post_form.is_valid():
                post = post_form.save(commit=False)
                post.author = request.user
                post.save()
                messages.success(request, 'Post created.')
                return redirect('profiles:detail', username=profile_user.username)
        else:
            post_form = PostForm()
    elif request.method == 'POST':
        return redirect('profiles:detail', username=profile_user.username)
    outgoing_request = None
    incoming_request = None
    if request.user.is_authenticated and request.user != profile_user:
        outgoing_request = FriendRequest.objects.filter(
            from_user=request.user, to_user=profile_user, status=FriendRequest.STATUS_PENDING
        ).first()
        incoming_request = FriendRequest.objects.filter(
            from_user=profile_user, to_user=request.user, status=FriendRequest.STATUS_PENDING
        ).first()
    status = _friend_status(request.user, profile_user)
    friend_count = Friendship.objects.filter(Q(user1=profile_user) | Q(user2=profile_user)).count()
    follower_count = (
        FriendRequest.objects.filter(
            to_user=profile_user, status__in=[FriendRequest.STATUS_PENDING, FriendRequest.STATUS_ACCEPTED]
        )
        .values('from_user')
        .distinct()
        .count()
    )
    return render(
        request,
        'profiles/detail.html',
        {
            'profile_user': profile_user,
            'profile': profile,
            'posts': posts,
            'post_form': post_form,
            'comment_form': comment_form,
            'comment_friend_flags': comment_friend_flags,
            'friend_status': status,
            'incoming_request': incoming_request,
            'outgoing_request': outgoing_request,
            'friend_count': friend_count,
            'follower_count': follower_count,
        },
    )


@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == 'POST' and 'remove_avatar' in request.POST:
        if profile.avatar:
            profile.avatar.delete(save=False)
            profile.avatar = None
            profile.save(update_fields=['avatar', 'updated_at'])
            messages.info(request, 'Avatar removed.')
        return redirect('profiles:edit')

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profiles:detail', username=request.user.username)
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'profiles/edit.html', {'form': form})
