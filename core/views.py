from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Conversation, Message # Assuming these are your Django models
from zhipuai import ZhipuAI
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

def deepsearch():
    from mypraisonaiagents import Agent, Agents, MCP
    brave_api_key = "BSAzbNViPbppE07cSHaKYV8dkcgCzz0"
    os.environ["BRAVE_API_KEY"] = brave_api_key
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")


    # Travel Research Agent
    research_agent = Agent(
        instructions="Research about travel destinations, attractions, local customs, and travel requirements",
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
    )

    # Flight Booking Agent
    flight_agent = Agent(
        instructions="Search for available flights, compare prices, and recommend optimal flight choices",
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
    )

    # Accommodation Agent
    hotel_agent = Agent(
        instructions="Research hotels and accommodation based on budget and preferences",
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
    )

    # Itinerary Planning Agent
    planning_agent = Agent(
        instructions="Design detailed day-by-day travel plans incorporating activities, transport, and rest time",
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
        tools=MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})
    )

    # Example usage - research travel destinations
    destination = "London, UK"
    dates = "August 15-22, 2025"
    budget = "Mid-range (£1000-£1500)"
    preferences = "Historical sites, local cuisine, avoiding crowded tourist traps"
    travel_query = f"What are the best attractions to visit in {destination} during {dates} on a budget of {budget} with preferences of {preferences}?"
    agents = Agents(agents=[research_agent, flight_agent, hotel_agent, 
                            planning_agent
                            ])

    result, tool_call_result = agents.start(travel_query, return_dict = True)
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
            user_query = body_data.get('query', '')
            if not user_query:
                return JsonResponse({"error": "Query cannot be empty"}, status=400)

            # Call the deepsearch function here
            result, tool_call_result = deepsearch()  # Assuming this is a function defined in your code

            agent_size = len(result["task_results"])

            agent_results = []
            for i in range(agent_size):
                agent_results.append({"llm_output": result["task_results"][i].raw, "llm_input": result["task_results"][i].description})
                # print(f"Agent {i} result: {result['task_results'][i].raw}")

            tool_results = []

            for i in range(len(tool_call_result)):
                if tool_call_result[i]:
                    tool_results.append(tool_call_result[i])
                else:
                    tool_results.append("None")
            print("all is fine")
            return JsonResponse({"message": "Deep search completed successfully.",
                                 "tool_results": tool_results,
                                 "agent_results": agent_results,
                                 })
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
        except Exception as e:
            print(f"Error in deepsearch view: {e}")
            return JsonResponse({"error": f"An unexpected server error occurred: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)


@csrf_exempt
def index(request): # Simple test endpoint
    return HttpResponse("Hello from core.index! The llm_talk endpoint is available for POST requests.")

