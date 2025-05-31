import uuid
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Conversation, Message # Assuming these are your Django models
from zhipuai import ZhipuAI
from django.utils.encoding import smart_str
from core.models import DeepSearchConversation
import os
import re
import json
from tool.map import * 
from tool.simple import *
from tool.conversation import *
from tool.user import *
from tool.travel_post import *
from tool.talk import *

import os
import re

def deepsearch(destination="Beijing, China", dates="August 15-22, 2025", budget="sufficient", preferences="no specific preferences", startpoint="from Beijing, China"):
    from mypraisonaiagents import Agent, Agents, MCP
    brave_api_key = "BSAzbNViPbppE07cSHaKYV8dkcgCzz0"
    os.environ["BRAVE_API_KEY"] = brave_api_key
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")
    os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "AIzaSyBh2w64uOFq6AFJFo1BVOy6znh-2C93_38")
    os.environ["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "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")

    travel_query = f"Make a travel plan for me in {destination} during {dates} on a budget of {budget} with preferences of {preferences}. I am currently in {startpoint}."
    instruction_map = {
        "research": "Research about travel destinations, attractions, local customs, and travel requirements",
        "planning": "Design detailed day-by-day travel plans incorporating activities, transport, and rest time"
    }

    # 各代理初始化
    research_agent = Agent(
        instructions=instruction_map["research"],
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
    )

    planning_agent = Agent(
        instructions=instruction_map["planning"],
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
    )

    agents = Agents(agents=[research_agent, planning_agent])

    result, tool_call_result = agents.start(travel_query, return_dict=True)
    print(f"\n=== DESTINATION RESEARCH: {destination} ===\n")
    print(result)
    print("\n=== TOOL CALL RESULT ===\n")
    print(tool_call_result)
    return result, tool_call_result

def airplane(start_date, end_date, startpoint, destination):
    from mypraisonaiagents import Agent, Agents, MCP
    os.environ["BRAVE_API_KEY"] = "BSAzbNViPbppE07cSHaKYV8dkcgCzz0"
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")
    os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "AIzaSyBh2w64uOFq6AFJFo1BVOy6znh-2C93_38")
    os.environ["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "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")
    os.environ["DUFFEL_ACCESS_TOKEN"] = "duffel_test_Li5UOd_hOzpiAwxv3GLp4lQ23Y8bkaXo86R216FMgD-"
    print(f"groq key {os.getenv('GROQ_API_KEY')}")

    judge_need_plane_agent = Agent(
        instructions="Judge whether a flight is needed based on the start date, end date, startpoint, and destination. If a flight is needed, output YES. Otherwise, output NO.",
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
    )
    judge_need_plane = judge_need_plane_agent.start(
        f"Do I need a flight from {startpoint} to {destination} between {start_date} and {end_date}?")
    
    print(f"Need flight: {judge_need_plane}")
    if "yes" in judge_need_plane[0].lower():
        flight_agent = Agent(
            instructions="Search for available flights, compare prices, and recommend optimal flight choices.",
            llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
            tools=MCP("python3 core/flight_mcp.py")
        )

        result1, tool_call_result1 = flight_agent.start(
            f"Find flights from {startpoint} to {destination} on {start_date}")
        result2, tool_call_result2 = flight_agent.start(
            f"Find flights from {destination} to {startpoint} on {end_date}")
        
        # print(f"\n=== FLIGHT SEARCH RESULT ===\n{result1} \n {tool_call_result1}")

        total_result = {
            "llm_output": f"From {startpoint} to {destination} flight \n{result1}\n\n From {destination} to {startpoint}\n {result2}",
            "tool_call_result": f"From {startpoint} to {destination} flight toolcall\n {tool_call_result1} \n\n From {destination} to {startpoint} flight toolcall\n {tool_call_result2}"
        }
        print(f"\n=== TOTAL FLIGHT SEARCH RESULT ===\n{total_result}")
        return total_result
    else:
        return {"message": "No flight needed."}

def hotel(start_date, end_date, destination):
    import datetime
    from mypraisonaiagents import Agent, Agents, MCP
    os.environ["AMADEUS_CLIENT_ID"] = "mcehOG8E8AAWpwdNLWFbYE41tNxoIqsk"
    os.environ["AMADEUS_CLIENT_SECRET"] = "6qKytIzAmaELkUP7"
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")
    agent = Agent(
        instructions=f"""search for hotel. Current date is {datetime.datetime.now().strftime('%Y-%m-%d')}.""",
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools = MCP("python3 core/hotel_mcp.py")
    )
    import json
    hotel_result, hotel_tool_call = agent.start(f"I want to search a hotel in {destination} from {start_date} to {end_date}.")
    total_reult = {
        "llm_output": hotel_result,
        "tool_call_result": json.loads(hotel_tool_call)
    }
    return total_reult


def summary(agent_results):
    from mypraisonaiagents import Agent, Agents
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")
    
    summary_agent = Agent(
        instructions="Summarize the travel plan based on the agent results and flight information. Select the most appropriate flight options, most appropriate hotel first. And then provide a detailed summary of the travel plan.",
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct"
    )
    
    # Combine all agent outputs into a single string
    combined_results = "\n".join([result["llm_output"] for result in agent_results])
    
    summary_result = summary_agent.start(combined_results)
    return summary_result


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
            startpoint = body_data.get('startpoint', 'from Beijing, China')  # 新增：接收 startpoint
            user_id = body_data.get('user_id', 3)  # 新增：接收 user_id
            conversationid = body_data.get('conversationid', "0")  # 新增：接收 conversationid

            start_data, end_data = dates.split(",")
            print(f"Start date: {start_data}, End date: {end_data}")
            airplane_result = airplane(start_data, end_data, startpoint, destination)
            hotel_result = hotel(start_data, end_data, destination)

        
            if not destination or not dates or not budget or not preferences:
                return JsonResponse({"error": "Query cannot be empty"}, status=400)

            # Step 1: Call deepsearch
            result, tool_call_result = deepsearch(destination=destination, budget=budget,
                                                  dates=dates, preferences=preferences, startpoint=startpoint)
            
            # Step 2: Format agent results
            agent_size = len(result["task_results"])
            agent_results = []
            for i in range(agent_size):
                agent_results.append({
                    "llm_output": result["task_results"][i].raw,
                    "llm_input": result["task_results"][i].description
                })
            agent_results.append({
                "llm_output": airplane_result["llm_output"],
                "llm_input": f"Find flights from {startpoint} to {destination} on {start_data} and return on {end_data}."
            })
            agent_results.append({
                "llm_output": hotel_result["llm_output"],
                "llm_input": f"Find hotels in {destination} from {start_data} to {end_data}."
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
            tool_results.append([{"airplane": airplane_result["tool_call_result"]}])
            tool_results.append([{"hotel": hotel_result["tool_call_result"]}])
            summary_result = summary(agent_results)
            tool_results.append([])
            agent_results.append({
                "llm_output": summary_result[0],
                "llm_input": "Summarize the travel plan based on the agent results."
            })
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

