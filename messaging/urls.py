from django.urls import path

from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.conversations_list, name='list'),
    path('<int:pk>/', views.conversation_detail, name='detail'),
    path('start/<str:username>/', views.start_conversation, name='start'),
]
