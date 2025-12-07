from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DirectMessageForm
from .models import DirectConversation
from .services import get_or_create_conversation, get_user_conversations, send_message

User = get_user_model()


@login_required
def conversations_list(request):
    conversations = (
        get_user_conversations(request.user)
        .annotate(last_message_at=Max('messages__created_at'))
        .order_by('-last_message_at', '-created_at')
        .prefetch_related('participants__user__profile')
    )
    return render(request, 'messaging/list.html', {'conversations': conversations})


@login_required
def conversation_detail(request, pk):
    conversation = get_object_or_404(
        DirectConversation.objects.prefetch_related(
            'participants__user__profile', 'messages__sender__profile', 'messages__sender'
        ),
        pk=pk,
        participants__user=request.user,
    )
    if request.method == 'POST':
        form = DirectMessageForm(request.POST, request.FILES)
        if form.is_valid():
            send_message(
                conversation,
                request.user,
                form.cleaned_data['content'],
                image=form.cleaned_data['image'],
            )
            return redirect('messaging:detail', pk=conversation.pk)
    else:
        form = DirectMessageForm()
    participants = list(conversation.participants.all())
    other_participants = [p.user for p in participants if p.user_id != request.user.id]
    chat_messages = conversation.messages.exclude(
        Q(sender=request.user, deleted_for_sender=True)
        | Q(~Q(sender=request.user), deleted_for_recipient=True)
    )
    return render(
        request,
        'messaging/detail.html',
        {
            'conversation': conversation,
            'chat_messages': chat_messages,
            'form': form,
            'other_participants': other_participants,
        },
    )


@login_required
def start_conversation(request, username):
    target = get_object_or_404(User, username=username)
    if request.method != 'POST':
        return redirect('profiles:detail', username=username)
    try:
        conversation = get_or_create_conversation(request.user, target, created_by=request.user)
        messages.success(request, 'Conversation ready.')
        return redirect('messaging:detail', pk=conversation.pk)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('profiles:detail', username=target.username)
