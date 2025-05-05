from django.contrib import admin
from .models import Chat, Message

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)
    filter_horizontal = ('participants',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'chat', 'timestamp')
    list_filter = ('chat', 'timestamp')
    search_fields = ('content', 'sender__username')
    readonly_fields = ('timestamp',)