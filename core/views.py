from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from tool.llm_helper import smart_talk
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import json
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Conversation, Message
from tool.user import user_login, create_user
from tool.travel_post import make_post, get_total_post_by_user_id, like_post, dislike_post, get_all_post
@csrf_exempt
def llm_talk(request):
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            user_query = body_data.get('query', '')
            conversation_id_str = body_data.get('conversation_id')
            user_id = body_data.get('user_id', -1)

            if conversation_id_str:
                print(f"there is conversation {conversation_id_str}")
                try:
                    conversation_id = int(conversation_id_str)
                    conversation = Conversation.objects.get(id=conversation_id)

                    if conversation.user_id != user_id:
                        return JsonResponse({"error": "user_id does not match the conversation"}, status=403)

                except (Conversation.DoesNotExist, ValueError):
                    try:
                        conversation_id = int(conversation_id_str)
                        conversation = Conversation(id=conversation_id, user_id=user_id)
                        conversation.save(force_insert=True)
                    except ValueError:
                        return JsonResponse({"error": "Invalid conversation_id"}, status=404)
            else:
                print(f"there is not conversation {conversation_id_str}")
                conversation = Conversation.objects.create(user_id=user_id)

            print(f"conversation id is {conversation.id} user_id is {conversation.user_id}")
            past_messages = Message.objects.filter(conversation=conversation).order_by('index')
            history = [{"role": m.role, "content": m.content} for m in past_messages]
            history.append({"role": "user", "content": user_query})
            print(f"history length is {len(history)}")

            # 在调用智能回复时包一层 try
            try:
                assistant_reply = smart_talk(history)
            except Exception as e:
                return JsonResponse({"error": f"smart_talk failed: {str(e)}"}, status=500)

            # 仅在成功获取 reply 后才保存
            next_index = past_messages.count()
            Message.objects.create(conversation=conversation, role='user', content=user_query, index=next_index)
            Message.objects.create(conversation=conversation, role='assistant', content=assistant_reply, index=next_index + 1)

            return JsonResponse({
                "llm_content": assistant_reply,
                "conversation_id": str(conversation.id)
            })

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

@csrf_exempt
def index(request):
    return HttpResponse("Hello from core.index!")

@csrf_exempt
def llm_talk_testing(request):
    print("calling llm talk")
    return JsonResponse({
        "llm_content": 
                         smart_talk([{"role":"user","content": "testing"}])
                         })

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
from .models import Conversation, Message


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
