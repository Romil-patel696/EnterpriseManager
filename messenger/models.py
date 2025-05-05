from django.db import models
from django.conf import settings

class Chat(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='chats'
    )
    is_group_chat = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        if self.is_group_chat and self.name:
            return f'Group: {self.name}'
        return f'Chat: {self.id}'
    
    def get_last_message(self):
        return self.messages.order_by('-timestamp').first()

class Message(models.Model):
    chat = models.ForeignKey(
        Chat, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='sent_messages'
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    attachment = models.FileField(
        upload_to='chat_attachments/', 
        blank=True, 
        null=True
    )
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f'{self.sender.username}: {self.content[:30]}...'