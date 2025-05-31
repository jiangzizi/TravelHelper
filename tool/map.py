import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Conversation, Message, DeepSearchConversation
from praisonaiagents import Agent, Agents, MCP
import requests
import concurrent.futures

def gaode_geo_info(locations, request_timeout=10, total_timeout=200):
    """
    并行获取高德地图经纬度信息，每个请求最大超时 request_timeout 秒，整体最多 total_timeout 秒
    :param locations: [{"Beijing": [116.4, 39.9]}, ...]
    :return: {"Beijing": {"longtitude": ..., "latitude": ..., "level": ...}, ...}
    """
    gaode_api_key = "fc60c58c6d919c5601b52fb5fcaee501"
    default_result = {
        "longtitude": -1,
        "latitude": -1,
        "level": "timeout"
    }

    def fetch_location(location):
        try:
            location_name = list(location.keys())[0]
            url = f"https://restapi.amap.com/v3/geocode/geo?address={location_name}&key={gaode_api_key}"
            response = requests.get(url, timeout=request_timeout)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == '1' and data['geocodes']:
                    location_info = data['geocodes'][0]
                    longitude, latitude = location_info['location'].split(',')
                    return location_name, {
                        "longtitude": float(longitude),
                        "latitude": float(latitude),
                        "level": location_info.get('level', 'unknown')
                    }
        except Exception as e:
            print(f"[ERROR] Location '{location}' failed: {e}")
        return list(location.keys())[0], default_result

    result = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch_location, loc) for loc in locations]
        try:
            for future in concurrent.futures.as_completed(futures, timeout=total_timeout):
                name, data = future.result()
                result[name] = data
        except concurrent.futures.TimeoutError:
            print("[ERROR] Total request time exceeded global timeout.")
            for future in futures:
                if not future.done():
                    name = list(locations[futures.index(future)].keys())[0]
                    result[name] = default_result

    return result


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
            os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")
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

            json_result = json.loads(result)
            gaode_result = gaode_geo_info(json_result)

            print(f"gaode result {gaode_result}")
            return JsonResponse({
                "llm_content": json_result,
                "gaode_result": gaode_result
                                })
        except Exception as e:
            return JsonResponse({"error": f"json decode error: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    





@csrf_exempt
def show_lattest_deepsearch_longtitude_latitude(request):
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            conversation_id = body_data.get('conversation_id')
            #user_id = body_data.get('user_id', -1)

            if not conversation_id:
                return JsonResponse({"error": "conversation_id is required"}, status=400)

            try:
                conversation = DeepSearchConversation.objects.get(conversationid=conversation_id)
            except DeepSearchConversation.DoesNotExist:
                return JsonResponse({"error": "Conversation not found"}, status=404)
            agent_results = conversation.agent_results or []
            if not agent_results:
                return JsonResponse({"error": "No agent_results found"}, status=404)

            latest_llm_output = agent_results[-1].get("llm_output", "")
            if not latest_llm_output:
                return JsonResponse({"error": "llm_output not found in latest agent_result"}, status=404)

            print(f"Latest llm_output: {latest_llm_output}")

            os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")
            google_map_agent = Agent(
                instructions="Perform map search to gather information",
                llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
                tools=MCP("npx -y @modelcontextprotocol/server-google-maps", env={
                    "GOOGLE_MAPS_API_KEY": "AIzaSyD8kz0EW1KKo8B3I8GU7nAy19R8S6X6RVE"
                })
            )

            agents = Agents(agents=[google_map_agent])

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
            {latest_llm_output}
            """

            result = agents.start(prompt)

            print(f"LLM raw result: {result}")

            json_result = json.loads(result)
            gaode_result = gaode_geo_info(json_result)

            return JsonResponse({
                "llm_content": json_result,
                "gaode_result": gaode_result
            })

        except Exception as e:
            return JsonResponse({"error": f"Internal server error: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405) 
