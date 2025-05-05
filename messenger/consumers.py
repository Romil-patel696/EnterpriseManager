import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Chat, Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f'chat_{self.chat_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.chat_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.chat_group_name,
            self.channel_name
        )
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        
        # Save the message to the database
        saved_message = await self.save_message(message)
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_username': self.user.username,
                'sender_id': self.user.id,
                'timestamp': saved_message['timestamp'],
                'message_id': saved_message['id']
            }
        )
    
    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender_username': event['sender_username'],
            'sender_id': event['sender_id'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id']
        }))
    
    @database_sync_to_async
    def save_message(self, content):
        chat = Chat.objects.get(id=self.chat_id)
        message = Message.objects.create(
            chat=chat,
            sender=self.user,
            content=content
        )
        return {
            'id': message.id,
            'timestamp': message.timestamp.strftime('%b %d, %Y, %I:%M %p')
        }