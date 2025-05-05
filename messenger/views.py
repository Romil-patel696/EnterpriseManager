from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth import get_user_model

from .models import Chat, Message

User = get_user_model()

@login_required
def chat_list(request):
    """Display list of chats for the current user"""
    chats = Chat.objects.filter(participants=request.user).order_by('-updated_at')
    
    # Get users for starting new chats
    users = User.objects.exclude(id=request.user.id)
    
    context = {
        'chats': chats,
        'users': users,
    }
    
    return render(request, 'messenger/chat_list.html', context)

@login_required
def chat_detail(request, chat_id):
    """Display chat detail and allow sending messages"""
    chat = get_object_or_404(Chat, id=chat_id, participants=request.user)
    messages = chat.messages.all()
    
    # Mark messages as read
    unread_messages = messages.filter(is_read=False).exclude(sender=request.user)
    unread_messages.update(is_read=True)
    
    context = {
        'chat': chat,
        'messages': messages,
    }
    
    return render(request, 'messenger/chat_detail.html', context)

@login_required
def new_chat(request):
    """Create a new chat with selected users"""
    if request.method == 'POST':
        user_ids = request.POST.getlist('users')
        
        if not user_ids:
            return redirect('messenger:chat_list')
        
        # Check if it's a group chat
        is_group = len(user_ids) > 1 or request.POST.get('is_group', False)
        name = request.POST.get('name', '')
        
        # For one-on-one chats, check if a chat already exists
        if not is_group and len(user_ids) == 1:
            existing_chat = Chat.objects.filter(
                participants=request.user,
                is_group_chat=False
            ).filter(participants=user_ids[0])
            
            if existing_chat.count() == 1:
                return redirect('messenger:chat_detail', chat_id=existing_chat.first().id)
        
        # Create new chat
        chat = Chat.objects.create(
            name=name,
            is_group_chat=is_group
        )
        
        # Add participants
        chat.participants.add(request.user)
        for user_id in user_ids:
            chat.participants.add(user_id)
        
        return redirect('messenger:chat_detail', chat_id=chat.id)
    
    return redirect('messenger:chat_list')

@login_required
def send_message(request, chat_id):
    """Send a message in a chat"""
    if request.method == 'POST':
        chat = get_object_or_404(Chat, id=chat_id, participants=request.user)
        content = request.POST.get('content', '').strip()
        
        if content:
            message = Message.objects.create(
                chat=chat,
                sender=request.user,
                content=content
            )
            
            # Handle file attachment if present
            if request.FILES.get('attachment'):
                message.attachment = request.FILES['attachment']
                message.save()
            
            # Update chat's updated_at timestamp
            chat.save()  # This triggers auto_now=True
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message_id': message.id,
                    'content': message.content,
                    'timestamp': message.timestamp.strftime('%b %d, %Y, %I:%M %p'),
                    'sender': message.sender.username
                })
        
    return redirect('messenger:chat_detail', chat_id=chat_id)