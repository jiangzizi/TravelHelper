
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def get_user_conversation_ids(request):
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            user_id = body_data.get('user_id', None)

            if user_id is None:
                return JsonResponse({"error": "user_id is required"}, status=400)

            conversations = Conversation.objects.filter(user_id=user_id)
            conversation_ids = [conv.id for conv in conversations]

            return JsonResponse({
                "conversation_ids": conversation_ids
            })

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from core.models import Conversation, Message


def filter_message_alternation(messages):
    """确保消息交替出现：user -> assistant -> user -> assistant"""
    filtered = []
    last_role = None
    for msg in messages:
        if msg.role == last_role and msg.role == 'user':
            continue  # 删除连续的第二条 user
        filtered.append(msg)
        last_role = msg.role
    return filtered


@csrf_exempt
def get_conversation_content(request):
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            user_id = body_data.get('user_id', None)

            if user_id is None:
                return JsonResponse({"error": "user_id is required"}, status=400)

            print(f"get_conversation_content user_id is {user_id}")
            conversations = Conversation.objects.filter(user_id=user_id)
            if not conversations:
                return JsonResponse({"error": "No conversations found for this user"}, status=404)

            conversation_data = []

            for conversation in conversations:
                messages = Message.objects.filter(conversation=conversation).order_by('index')
                filtered_messages = filter_message_alternation(messages)
                message_history = [{"role": m.role, "content": m.content} for m in filtered_messages]

                conversation_data.append({
                    "conversation_id": str(conversation.id),
                    "messages": message_history
                })

            return JsonResponse({
                "conversations": conversation_data
            })

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)


@csrf_exempt
def get_conversation_content_by_id(request):
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            user_id = body_data.get('user_id', None)
            conversation_id_str = body_data.get('conversation_id', None)

            if user_id is None or conversation_id_str is None:
                return JsonResponse({"error": "user_id and conversation_id are required"}, status=400)

            try:
                conversation_id = int(conversation_id_str)
                conversation = Conversation.objects.get(id=conversation_id)
            except (ValueError, Conversation.DoesNotExist):
                return JsonResponse({"error": "Invalid conversation_id"}, status=404)

            if conversation.user_id != user_id:
                return JsonResponse({"error": "user_id does not match the conversation"}, status=403)

            messages = Message.objects.filter(conversation=conversation).order_by('index')
            filtered_messages = filter_message_alternation(messages)
            message_history = [{"role": m.role, "content": m.content} for m in filtered_messages]

            return JsonResponse({
                "conversation_id": str(conversation.id),
                "messages": message_history
            })

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)
