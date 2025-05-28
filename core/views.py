from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Conversation, Message # Assuming these are your Django models
from zhipuai import ZhipuAI
from core.models import DeepSearchConversation
import os
import re
import json
from tool.map import * # Assuming these are not directly used in the provided snippet
from tool.simple import *
from tool.conversation import *
from tool.user import *
from tool.travel_post import *
from tool.talk import *

import os
import re

def deepsearch(destination="Beijing, China", dates="August 15-22, 2025", budget="sufficient", preferences="no specific preferences"):
    from mypraisonaiagents import Agent, Agents, MCP
    brave_api_key = "BSAzbNViPbppE07cSHaKYV8dkcgCzz0"
    os.environ["BRAVE_API_KEY"] = brave_api_key
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")

    # 判断输入是否为中文
    def is_chinese(text):
        return re.search(r'[\u4e00-\u9fff]', text) is not None

    # 中文还是英文提示词
    if is_chinese(destination + preferences + dates + budget):
        travel_query = f"请帮我制定一个{dates}在{destination}的旅行计划，预算是{budget}，偏好是：{preferences}。"
        instruction_map = {
            "research": "请研究旅行目的地、景点推荐、当地习俗和出入境要求",
            "flight": "请搜索可用航班、比较票价并推荐最优航班方案",
            "hotel": "请根据预算和偏好搜索住宿酒店",
            "planning": "请制定一个详细的逐日旅行计划，包含活动安排、交通和休息时间"
        }
    else:
        travel_query = f"Make a travel plan for me in {destination} during {dates} on a budget of {budget} with preferences of {preferences}."
        instruction_map = {
            "research": "Research about travel destinations, attractions, local customs, and travel requirements",
            "flight": "Search for available flights, compare prices, and recommend optimal flight choices",
            "hotel": "Research hotels and accommodation based on budget and preferences",
            "planning": "Design detailed day-by-day travel plans incorporating activities, transport, and rest time"
        }

    # 各代理初始化
    research_agent = Agent(
        instructions=instruction_map["research"],
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
    )

    flight_agent = Agent(
        instructions=instruction_map["flight"],
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
    )

    hotel_agent = Agent(
        instructions=instruction_map["hotel"],
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
    )

    planning_agent = Agent(
        instructions=instruction_map["planning"],
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
    )

    agents = Agents(agents=[
        research_agent, flight_agent, hotel_agent, planning_agent
    ])

    result, tool_call_result = agents.start(travel_query, return_dict=True)
    print(f"\n=== DESTINATION RESEARCH: {destination} ===\n")
    print(result)
    print("\n=== TOOL CALL RESULT ===\n")
    print(tool_call_result)
    return result, tool_call_result



@csrf_exempt
def answer_deepsearch(request):
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            destination = body_data.get('destination', '')
            dates = body_data.get('dates', '')
            budget = body_data.get('budget', '')
            preferences = body_data.get('preferences', '')
            user_id = body_data.get('user_id', 3)  # 新增：接收 user_id
            conversationid = body_data.get('conversationid', "0")  # 新增：接收 conversationid

            if not destination or not dates or not budget or not preferences:
                return JsonResponse({"error": "Query cannot be empty"}, status=400)

            # Step 1: Call deepsearch
            result, tool_call_result = deepsearch(destination=destination, budget=budget,
                                                  dates=dates, preferences=preferences)

            # Step 2: Format agent results
            agent_size = len(result["task_results"])
            agent_results = []
            for i in range(agent_size):
                agent_results.append({
                    "llm_output": result["task_results"][i].raw,
                    "llm_input": result["task_results"][i].description
                })

            # Step 3: Parse tool results
            def parse_search_results(results_str):
                raw_results = results_str.strip().split("\n\n")
                parsed_results = []
                for res in raw_results:
                    lines = res.split("\n")
                    entry = {}
                    for line in lines:
                        if ": " in line:
                            key, value = line.split(": ", 1)
                            entry[key.lower()] = value
                    if entry:
                        parsed_results.append(entry)
                return parsed_results

            tool_results = []
            for i in range(len(tool_call_result)):
                if tool_call_result[i]:
                    parsed = parse_search_results(tool_call_result[i])
                    tool_results.append(parsed)
                else:
                    tool_results.append(None)

            # Step 4: Save into DB
            conv = DeepSearchConversation.objects.create(
                conversationid=conversationid, #or str(uuid.uuid4()),  # 如果没传就生成一个 UUID
                user_id=user_id or 0,
                destination=destination,
                budget=budget,
                dates=dates,
                preferences=preferences,
                tool_results=tool_results,
                agent_results=agent_results
            )

            print("Conversation saved:", conv.id)

            # Step 5: Return response
            return JsonResponse({
                "message": "Deep search completed successfully.",
                "tool_results": tool_results,
                "agent_results": agent_results
            })

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
        except Exception as e:
            print(f"Error in deepsearch view: {e}")
            return JsonResponse({"error": f"An unexpected server error occurred: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)


@csrf_exempt
def get_deepsearch_conversation_ids_by_user(request):
    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        if not user_id:
            return JsonResponse({"error": "Missing user_id"}, status=400)
        
        try:
            conversations = DeepSearchConversation.objects.filter(user_id=user_id)
            ids = [conv.conversationid for conv in conversations]
            return JsonResponse({"conversation_ids": ids}, status=200)
        except Exception as e:
            print(f"Error fetching conversations: {e}")
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only GET method is allowed"}, status=405)

from django.core.serializers.json import DjangoJSONEncoder

@csrf_exempt
def get_deepsearch_conversation_by_id(request):
    if request.method == 'GET':
        conversationid = request.GET.get('conversationid')
        if not conversationid:
            return JsonResponse({"error": "Missing conversationid"}, status=400)
        
        try:
            conv = DeepSearchConversation.objects.get(conversationid=conversationid)
            data = {
                "conversationid": conv.conversationid,
                "user_id": conv.user_id,
                "destination": conv.destination,
                "budget": conv.budget,
                "dates": conv.dates,
                "preferences": conv.preferences,
                "tool_results": conv.tool_results,
                "agent_results": conv.agent_results,
            }
            return JsonResponse(data, status=200)
        except DeepSearchConversation.DoesNotExist:
            return JsonResponse({"error": "Conversation not found"}, status=404)
        except Exception as e:
            print(f"Error fetching conversation: {e}")
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only GET method is allowed"}, status=405)


@csrf_exempt
def index(request): # Simple test endpoint
    return HttpResponse("Hello from core.index! The llm_talk endpoint is available for POST requests.")

