import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Conversation, Message
from praisonaiagents import Agent, Agents, MCP

import requests
def gaode_geo_info(locations):
    gaode_result = {}
    """根据高德地图API获取经纬度"""
    for item in locations:
        print(f"item is {item}")
        print(f"item keys {item.keys()}")
        location = list(item.keys())[0]  # 正确访问第一个 key
        url = f"https://restapi.amap.com/v3/geocode/geo?address={location}&key=fc60c58c6d919c5601b52fb5fcaee501"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == '1' and data['geocodes']:
                location_info = data['geocodes'][0]
                longitude = location_info['location'].split(',')[0]
                latitude = location_info['location'].split(',')[1]
                level = location_info['level']
                print(f"Location: {location}, Longitude: {longitude}, Latitude: {latitude}")
                gaode_result[location] = {
                    "longtitude": longitude,
                    "latitude": latitude,
                    "level": level
                }
            else:
                print(f"Location: {location} not found.")
        else:
            print(f"Error: Unable to fetch data for {location}. Status code: {response.status_code}")
    return gaode_result


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