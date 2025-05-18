from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from tool.llm_helper import smart_talk
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Conversation, Message
from tool.user import user_login, create_user
from tool.travel_post import make_post, get_total_post_by_user_id, like_post, dislike_post, get_all_post
from zhipuai import ZhipuAI
import json
from praisonaiagents import Agent, Agents, MCP
import os
from tool.conversation import *


def should_search(message_list):
    """判断是否需要搜索"""
    client = ZhipuAI(api_key="0982eaa8f53f4d649e003336000451c5.E5OuhWgc7pAtHeJf")
    
    # 系统提示，明确告诉模型只需要回答是否需要搜索
    system_prompt = {
        "role": "system",
        "content": """Decide whether you need to call web search function to answer user's query. Only output 'YES' or 'NO'.
        Output 'YES' if use ask for weather, directions, local food, detailed travel planing, longitude or latitude search  .
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
    brave_api_key = "BSAzbNViPbppE07cSHaKYV8dkcgCzz0" #     os.getenv("BRAVE_API_KEY")
    os.environ["BRAVE_API_KEY"] = brave_api_key
    os.environ["GROQ_API_KEY"] = "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"

    # General Search Agent
    general_search_agent = Agent(
        instructions="Perform general web searches to gather information",
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
    )
    google_map_agent = Agent(
         instructions="Perform map search to gather information",
         llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
         tools=MCP("npx -y @modelcontextprotocol/server-google-maps", env={"GOOGLE_MAPS_API_KEY": "AIzaSyD8kz0EW1KKo8B3I8GU7nAy19R8S6X6RVE"})
    )
    agents = Agents(agents=[general_search_agent, 
                            google_map_agent
                            ])
    result = agents.start(query)
    print(f"search result {result}")
    return result

def extract_longtitude_latitude(query):
    client = ZhipuAI(api_key="0982eaa8f53f4d649e003336000451c5.E5OuhWgc7pAtHeJf")
    
    # 系统提示，明确告诉模型只需要回答是否需要搜索
    system_prompt = {
        "role": "system",
        "content": """Extract longitude and latitude from the query. If there is no longitude and latitude, only output one word 'None'.
        Otherwise, only output the longitude and latitude in the format of '[longitude,latitude]'.
        Strictly follow the format. DO NOT add any other content.
        """
    }

    # 构建消息列表
    messages = [system_prompt] + [{"role": "user", "content": "Try to extract longitude and latitude from below content. \n"+query}]
    
    response = client.chat.completions.create(
        model="glm-4-flash",
        messages=messages,
        max_tokens=128
    )
    
    output = response.choices[0].message.content.strip().upper()
    #print(f"search decision {decision}")
    print(f"extract longtitude and latitude decision {output}")
    return output

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
    if basic:
        return {
                "direct_answer": generate_final_response(message_list), 
                "seearch_result":"None",
                "longtitude_latitude": "None"
                
            }
    if should_search(message_list):
        search_results = perform_search(user_query)
        return {
                "direct_answer": generate_final_response(message_list, search_results), 
                "search_result": search_results,
                "longtitude_latitude": extract_longtitude_latitude(search_results)
        }
    else:
        # 如果不需要搜索，直接生成回复
        return {
                "direct_answer": generate_final_response(message_list),
                "search_result": "None",
                "longtitude_latitude": "None"
        }


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
                reply = smart_talk(history, basic=False)
            except Exception as e:
                return JsonResponse({"error": f"smart_talk failed: {str(e)}"}, status=500)

            assistant_reply = reply.get("direct_answer", "Sorry, I cannot answer your question.")
            search_result = reply.get("search_result", "None")
            longtitude_latitude = reply.get("longtitude_latitude", "None")


            # 仅在成功获取 reply 后才保存
            next_index = past_messages.count()
            Message.objects.create(conversation=conversation, role='user', content=user_query, index=next_index)
            Message.objects.create(conversation=conversation, role='assistant', content=assistant_reply, index=next_index + 1)

            return JsonResponse({
                "llm_content": assistant_reply,
                "conversation_id": str(conversation.id),
                "search_result": search_result,
                "longtitude_latitude": longtitude_latitude
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
def show_lattest_longtitude_latitude(request):
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
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
                return JsonResponse({"error": "conversation_id is required"}, status=400)

            print(f"conversation id is {conversation.id} user_id is {conversation.user_id}")
            past_messages = Message.objects.filter(conversation=conversation).order_by('index')
            # history = [{"role": m.role, "content": m.content} for m in past_messages]
            # history.append({"role": "user", "content": user_query})
            # print(f"history length is {len(history)}")
            lattest_content = past_messages.last().content
            print(f"lattest content is {lattest_content}")
            print("calling show_lattest_longtitude_latitude")
            os.environ["GROQ_API_KEY"] = "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"
            google_map_agent = Agent(
                instructions="Perform map search to gather information",
                llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
                tools=MCP("npx -y @modelcontextprotocol/server-google-maps", env={"GOOGLE_MAPS_API_KEY": "AIzaSyD8kz0EW1KKo8B3I8GU7nAy19R8S6X6RVE"})
            )
            agents = Agents(agents=[ 
                                    google_map_agent
                                    ])

            prompt = f"""
            Extract all location names from the following text, then search for their longtitude and lantitude.

            If a location does not have a pair of coordinates, ignore it.

            Output the result strictly as a JSON list. Each item in the list should be a JSON object in the format:  
            {{ "location_name": [longitude, latitude] }}  
            Do not include any other text, explanation, or comments. Only return the JSON list.

            Example input:  
            "I want to visit Beijing and Shanghai."

            Example output:  
            [
            {{ "Beijing": [116.4074, 39.9042] }},
            {{ "Shanghai": [121.4737, 31.2304] }}
            ]

            Now process the following input:  
            {lattest_content}
            """

            # 假设你正在使用某个支持 agents.start() 的大模型框架
            result = agents.start(prompt)

            # 打印结果
            print(result)

            return JsonResponse({
                "llm_content": result,
                                })
        except Exception as e:
            return JsonResponse({"error": f"json decode error: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)