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
from zhipuai import ZhipuAI
import json
from praisonaiagents import Agent, Agents, MCP
import os

brave_api_key = "BSAzbNViPbppE07cSHaKYV8dkcgCzz0" #     os.getenv("BRAVE_API_KEY")
os.environ["BRAVE_API_KEY"] = brave_api_key
os.environ["GROQ_API_KEY"] = "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"

# General Search Agent
general_search_agent = Agent(
    instructions="Perform general web searches to gather information",
    llm="groq/llama-3.1-8b-instant",
    tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
)

def general_query(query):
    # Here you can implement the logic to process the query
    # For example, you can call the agents to get information
    # and return the results.
    agents = Agents(agents=[general_search_agent])
    result = agents.start(query)
    return result


def should_search(message_list):
    """判断是否需要搜索"""
    client = ZhipuAI(api_key="0982eaa8f53f4d649e003336000451c5.E5OuhWgc7pAtHeJf")
    
    # 系统提示，明确告诉模型只需要回答是否需要搜索
    system_prompt = {
        "role": "system",
        "content": """Decide whether you need to call web search function to answer user's query. Only output 'YES' or 'NO'.
        Output 'YES' if use ask for weather.
        """
    }

    # 构建消息列表
    messages = [system_prompt] + [message_list[-1]]
    print(f"should search {messages}")
    
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=messages,
        max_tokens=10
    )
    
    decision = response.choices[0].message.content.strip().upper()
    print(f"search decision {decision}")
    return decision == "YES"

def perform_search(query):
    print(f"perform search {query}")
    """执行搜索"""
    answer = general_query(query)
    print(f"search result {answer}")
    return answer

import re

def keep_after_last_function_tag(s):
    match = re.search(r'</function>(.*)$', s, re.DOTALL)
    return match.group(1) if match else s

def generate_final_response(message_list, search_results=None):
    """生成最终回复"""
    client = ZhipuAI(api_key="0982eaa8f53f4d649e003336000451c5.E5OuhWgc7pAtHeJf")
    print(f"search result for final generation is  {search_results}")
    search_results = keep_after_last_function_tag(search_results) if search_results else None
    print(f"search result for final generation is  {search_results}")
    system_prompt = {
        "role": "system",
        "content": "Your are a helpful travel assistant. You can only answer travel related questions."
    }
    
    # 如果有搜索结果，添加到消息中
    messages = [system_prompt]
    messages.extend(message_list)
    if search_results:
        messages[-1]["content"] += f"\n Answer my question based on below information.\n\n Here is the web search content \n{search_results}\n"

    # 添加历史消息和最新问题
    print(f"messages for final generation {messages}")
    
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=messages
    )
    
    return response.choices[0].message.content

def smart_talk(message_list, basic = True):
    """智能对话流程，包含搜索判断"""
    # 获取最新用户问题（假设是最后一条用户消息）
    latest_user_message = next((msg for msg in reversed(message_list) if msg["role"] == "user"), None)

    if not latest_user_message:
        return "请提出您的问题。"
    
    user_query = latest_user_message["content"]
    if basic :
        return generate_final_response(message_list), "None"
    # 第一步：判断是否需要搜索
    if should_search(message_list):
        # 第二步：如果需要搜索，执行搜索
        search_results = perform_search(user_query)
        # 第三步：结合搜索结果生成最终回复
        return generate_final_response(message_list, search_results), search_results
    else:
        # 如果不需要搜索，直接生成回复
        return generate_final_response(message_list), "None"


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
                assistant_reply, search_result = smart_talk(history, basic=False)
            except Exception as e:
                return JsonResponse({"error": f"smart_talk failed: {str(e)}"}, status=500)

            # 仅在成功获取 reply 后才保存
            next_index = past_messages.count()
            Message.objects.create(conversation=conversation, role='user', content=user_query, index=next_index)
            Message.objects.create(conversation=conversation, role='assistant', content=assistant_reply, index=next_index + 1)

            return JsonResponse({
                "llm_content": assistant_reply,
                "conversation_id": str(conversation.id),
                "search_result": search_result
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
