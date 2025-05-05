from django.urls import path
from . import views

app_name = 'messenger'

urlpatterns = [
    path('', views.chat_list, name='chat_list'),
    path('chat/<int:chat_id>/', views.chat_detail, name='chat_detail'),
    path('chat/new/', views.new_chat, name='new_chat'),
    path('chat/<int:chat_id>/send/', views.send_message, name='send_message'),
]