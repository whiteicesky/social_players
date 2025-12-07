from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from posts.models import Post

User = get_user_model()


@login_required
def search(request):
    query = request.GET.get('q', '').strip()
    user_results = []
    post_results = []
    if query:
        normalized = query.lower()
        normalized_clean = normalized.replace('_', ' ').replace('-', ' ')
        topic_matches = []
        for slug, label in Post.TOPIC_CHOICES:
            label_clean = label.lower()
            if normalized_clean in slug.replace('_', ' ') or normalized_clean in label_clean:
                topic_matches.append(slug)
        user_results = (
            User.objects.filter(Q(username__icontains=query) | Q(profile__display_name__icontains=query))
            .select_related('profile')
            .distinct()
        )
        post_results = (
            Post.objects.filter((Q(content__icontains=query) | Q(topic__in=topic_matches)), is_deleted=False)
            .select_related('author', 'author__profile')
            .distinct()
        )
    return render(request, 'core/search.html', {'query': query, 'user_results': user_results, 'post_results': post_results})
