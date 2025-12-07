from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import FriendRequest
from .services import (
    accept_friend_request,
    cancel_friend_request,
    get_friends_queryset,
    reject_friend_request,
    remove_friendship,
    send_friend_request,
)

User = get_user_model()


@login_required
def friends_list(request):
    friends = get_friends_queryset(request.user).select_related('profile')
    return render(request, 'friendships/friends_list.html', {'friends': friends})


@login_required
def incoming_requests(request):
    requests = FriendRequest.objects.filter(to_user=request.user, status=FriendRequest.STATUS_PENDING).select_related(
        'from_user__profile', 'to_user__profile'
    )
    return render(request, 'friendships/incoming_requests.html', {'requests': requests})


@login_required
def outgoing_requests(request):
    requests = FriendRequest.objects.filter(from_user=request.user, status=FriendRequest.STATUS_PENDING).select_related(
        'from_user__profile', 'to_user__profile'
    )
    return render(request, 'friendships/outgoing_requests.html', {'requests': requests})


@login_required
def send_request(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if request.method != 'POST':
        return redirect('profiles:detail', username=target.username)
    try:
        send_friend_request(request.user, target)
        messages.success(request, 'Friend request sent.')
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('profiles:detail', username=target.username)


@login_required
def accept_request_view(request, pk):
    friend_request = get_object_or_404(FriendRequest, pk=pk, to_user=request.user)
    if request.method != 'POST':
        return redirect('friendships:incoming')
    try:
        accept_friend_request(friend_request)
        messages.success(request, 'Friend request accepted.')
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('friendships:incoming')


@login_required
def reject_request_view(request, pk):
    friend_request = get_object_or_404(FriendRequest, pk=pk, to_user=request.user)
    if request.method != 'POST':
        return redirect('friendships:incoming')
    try:
        reject_friend_request(friend_request)
        messages.success(request, 'Friend request rejected.')
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('friendships:incoming')


@login_required
def cancel_request_view(request, pk):
    friend_request = get_object_or_404(FriendRequest, pk=pk, from_user=request.user)
    if request.method != 'POST':
        return redirect('friendships:outgoing')
    try:
        cancel_friend_request(friend_request)
        messages.info(request, 'Friend request cancelled.')
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('friendships:outgoing')


@login_required
def remove_friend(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if request.method != 'POST':
        return redirect('profiles:detail', username=target.username)
    remove_friendship(request.user, target)
    messages.info(request, 'Removed friend.')
    return redirect('profiles:detail', username=target.username)
