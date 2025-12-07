from django.urls import path

from . import views

app_name = 'posts'

urlpatterns = [
    path('social/', views.social_players, name='social_players'),
    path('social/topic/<slug:slug>/', views.topic_posts, name='topic_posts'),
    path('', views.feed, name='feed'),
    path('posts/<int:pk>/edit/', views.post_edit, name='post_edit'),
    path('posts/<int:pk>/delete/', views.post_delete, name='post_delete'),
    path('posts/<int:pk>/comment/', views.add_comment_view, name='add_comment'),
    path('comments/<int:pk>/delete/', views.delete_comment, name='delete_comment'),
    path('posts/<int:pk>/like/', views.toggle_like_view, name='toggle_like'),
]
