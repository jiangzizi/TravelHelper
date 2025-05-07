from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from tool.llm_helper import basic_talk
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import json
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Conversation, Message


@csrf_exempt
def llm_talk(request):
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            user_query = body_data.get('query', '')
            conversation_id_str = body_data.get('conversation_id')

            # 判断是否已有对话
            if conversation_id_str:
                print(f"there is conversation {conversation_id_str}")
                try:
                    conversation_id = int(conversation_id_str)
                    conversation = Conversation.objects.get(id=conversation_id)
                except (Conversation.DoesNotExist, ValueError):
                    try:
                        conversation_id = int(conversation_id_str)
                        conversation = Conversation(id=conversation_id)
                        conversation.save(force_insert=True)  # 强行指定主键插入
                    except ValueError:
                        return JsonResponse({"error": "Invalid conversation_id"}, status=404)
            else:
                print(f"there is not conversation {conversation_id_str}")
                conversation = Conversation.objects.create()

            # 获取已有上下文
            past_messages = Message.objects.filter(conversation=conversation).order_by('index')
            history = [{"role": m.role, "content": m.content} for m in past_messages]
            history.append({"role": "user", "content": user_query})
            # print(f"history is {history}")

            assistant_reply = basic_talk(history)

            next_index = past_messages.count()
            Message.objects.create(conversation=conversation, role='user', content=user_query, index=next_index)
            Message.objects.create(conversation=conversation, role='assistant', content=assistant_reply, index=next_index + 1)

            return JsonResponse({
                "llm_content": assistant_reply,
                "conversation_id": str(conversation.id)  # 注意返回字符串
            })

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

def index(request):
    return HttpResponse("Hello from core.index!")

def llm_talk_testing(request):
    print("calling llm talk")
    return JsonResponse({
        "llm_content": 
                         basic_talk([{"role":"user","content": "testing"}])
                         })