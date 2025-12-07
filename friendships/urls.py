from django.urls import path

from . import views

app_name = 'friendships'

urlpatterns = [
    path('', views.friends_list, name='list'),
    path('requests/', views.incoming_requests, name='incoming'),
    path('requests/outgoing/', views.outgoing_requests, name='outgoing'),
    path('send/<int:user_id>/', views.send_request, name='send'),
    path('request/<int:pk>/accept/', views.accept_request_view, name='accept'),
    path('request/<int:pk>/reject/', views.reject_request_view, name='reject'),
    path('request/<int:pk>/cancel/', views.cancel_request_view, name='cancel'),
    path('remove/<int:user_id>/', views.remove_friend, name='remove'),
]
