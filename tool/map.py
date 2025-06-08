import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Conversation, Message, DeepSearchConversation
from praisonaiagents import Agent, Agents, MCP
import requests
import concurrent.futures
from math import radians, cos, sin, asin, sqrt
from sklearn.cluster import DBSCAN
import numpy as np
from serpapi import GoogleSearch

def map_geo_info_with_region_check(location_names, google_map_key, level='country', request_timeout=2, total_timeout=10):
    """
    并行获取 Google Maps 经纬度信息，并检查所有地点是否属于同一地区（如同一国家/城市）。
    
    参数:
        location_names: List[str] 地点名称列表
        google_map_key: str       Google Maps API key
        level: str                区域层级，常见有 'country', 'administrative_area_level_1', 'locality'
        request_timeout: float    每个请求的超时时间（秒）
        total_timeout: float      所有任务的最大总耗时（秒）
    
    返回:
        {
            'geo_info': {
                'Forbidden City': {'longitude': ..., 'latitude': ..., 'level': ..., 'region': 'China'},
                ...
            },
            'same_region': True/False,
            'region_set': {'China'}
        }
    """

    def fetch_info(name):
        geo_url = 'https://maps.googleapis.com/maps/api/geocode/json'
        try:
            # Step 1: 获取经纬度
            geo_params = {'address': name, 'key': google_map_key}
            geo_resp = requests.get(geo_url, params=geo_params, timeout=request_timeout).json()

            if geo_resp['status'] != 'OK' or not geo_resp['results']:
                return name, None

            result = geo_resp['results'][0]
            loc = result['geometry']['location']
            loc_level = result['types'][0] if result['types'] else 'unknown'

            # Step 2: 获取地区层级（如 country）
            components = result.get('address_components', [])
            region_name = None
            for comp in components:
                if level in comp['types']:
                    region_name = comp['long_name']
                    break

            return name, {
                'longitude': loc['lng'],
                'latitude': loc['lat'],
                'level': loc_level,
                'region': region_name or 'UNKNOWN'
            }

        except Exception:
            return name, None

    geo_info = {}
    region_set = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_info, name): name for name in location_names}
        for future in concurrent.futures.as_completed(futures, timeout=total_timeout):
            name = futures[future]
            try:
                loc_name, info = future.result()
                geo_info[loc_name] = info
                if info and 'region' in info:
                    region_set.add(info['region'])
                else:
                    region_set.add('UNKNOWN')
            except Exception:
                geo_info[name] = None
                region_set.add('UNKNOWN')

    return {
        'geo_info': geo_info,
        'same_region': len(region_set) == 1,
        'region_set': region_set
    }


def haversine(lon1, lat1, lon2, lat2):
    R = 6371.0
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    return 2 * R * asin(sqrt(a))

def cluster_close_locations(locations, eps_km=5):
    #print(f"Clustering locations with eps_km={eps_km}\n {locations}\n {locations.keys()}")
    geo_info = locations['geo_info']
    #print(f"Geo info: {geo_info.keys()}\n\n")
    names = list(geo_info.keys())
    #print(f"Names for clustering: {names}\n\n")
    coords = np.array([[v['latitude'], v['longitude']] for v in geo_info.values() if v is not None])

    #print(f"Coordinates for clustering: {coords}")

    dist_matrix = np.zeros((len(coords), len(coords)))
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            dist = haversine(coords[i][1], coords[i][0], coords[j][1], coords[j][0])
            dist_matrix[i][j] = dist_matrix[j][i] = dist
    #print(f"Distance matrix: {dist_matrix}")
    clustering = DBSCAN(eps=eps_km, min_samples=2, metric='precomputed').fit(dist_matrix)
    labels = clustering.labels_
    #print(f"Clustering labels: {labels}")
    clusters = {}
    for label, name, coord in zip(labels, names, coords):
        if label == -1:
            continue
        clusters.setdefault(int(label), []).append({
            'name': name,
            'latitude': float(coord[0]),
            'longitude': float(coord[1])
        })

    return clusters


def get_place_images(place_names, serpapi_key, real_search = True):
    print(f"Fetching images for places: {place_names}")
    images = {}
    for place in place_names:
        images[place] = ["https://www.example.com/image.jpg"]  # Placeholder for actual image fetching logic
        if real_search:
            try:
                params = {
                    "q": place,
                    "engine": "google_images_light",
                    "api_key": serpapi_key
                }
                search = GoogleSearch(params)
                results = search.get_dict()
                image_urls = []
                if 'images_results' in results and results['images_results']:
                    for image in results['images_results']:
                        if 'thumbnail' in image:
                            image_urls.append(image['thumbnail'])
                    images[place] = image_urls
            except Exception as e:
                print(f"Error fetching image for {place}: {e}")

    return images

def get_llm_ratings(place_names):
    print(f"Fetching LLM ratings for places: {place_names}")
    ratings = {}
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")
    agent = Agent(llm="groq/meta-llama/llama-4-scout-17b-16e-instruct", instructions= "Generate a rating for the following places based on their popularity and significance. The rating should be a float number between 1 and 5, where 1 is the lowest and 5 is the highest. Be strict and avoid rating all places a 5.0. Output your rating in a JSON format with the place name as the key and the rating as the value. Do not include any other information.")

    result = agent.start(f"Generate a rating for the following places: {', '.join(place_names)}")
    print(f"LLM raw result: {result}")
    import re
    match = re.search(r'\{.*?\}', result, re.DOTALL)
    if match:
        ratings = json.loads(match.group(0))
    else:
        print("No valid JSON found in LLM output.")

    return ratings  # Placeholder for actual LLM rating fetching logic

def get_llm_free_charge(place_names):
    print(f"Fetching LLM free charge for places: {place_names}")
    free_charge = {}
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")
    agent = Agent(llm="groq/meta-llama/llama-4-scout-17b-16e-instruct", instructions= "Generate a boolean value indicating whether the following places is free to visit or not. Output your result in a JSON format with the place name as the key and a boolean value as the value. Do not include any other information. Places that are free to visit should be marked as true, and those that require a fee should be marked as false. Places that are free to visit include parks, public squares, museums, universities and libraries.")
    result = agent.start(f"Do the following places have free charge: {', '.join(place_names)}")
    print(f"LLM raw result: {result}")
    import re
    match = re.search(r'\{.*?\}', result, re.DOTALL)
    if match:
        free_charge = json.loads(match.group(0))
    else:
        print("No valid JSON found in LLM output.")
    return free_charge  # Placeholder for actual LLM free charge fetching logic

def extract_clusters(latest_llm_output, instruction, image_search=False):
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")
    import json


    # 创建 Agent
    full_instruction = (
    f"{instruction}\n"
    "Output only a JSON list of dictionaries, where each dictionary contains a travel attraction name as the key and its description as the value.\n"
    "Example output:\n"
    "[\n"
    "  {\"Eiffel Tower\": \"The Eiffel Tower, located in Paris, is a wrought-iron lattice tower built in 1889 for the World's Fair. Standing 324 meters tall, it’s a global symbol of France and a major tourist attraction. Its unique design and stunning views make it an architectural marvel and cultural icon.\"},\n"
    "  {\"Louvre Museum\": \"The Louvre Museum in Paris is the world's largest art museum and a historic monument. It houses over 380,000 objects, including the Mona Lisa and the Venus de Milo. The museum's glass pyramid entrance is an architectural highlight.\"}\n"
    "]"
)

    agent = Agent(
        instructions=full_instruction,
        llm="groq/meta-llama/llama-4-scout-17b-16e-instruct",
    )

    result = agent.start(f"""Extract and only extract the main tourist attractions like parks, must-visit spots, universities, landmarks, museums or other kinds of trip spots from the following text section \n\n{latest_llm_output}\n\n Do not include any other information""")
    import re, json

    match = re.search(r'\[.*?\]', result, re.DOTALL)
    if match:
        attractions = json.loads(match.group(0))
    else:
        attractions = []

    if not attractions:
        return {}

    print(f"LLM raw result: {attractions}")
    places = []
    attraction_map = {}
    for place in attractions:
        print(f"Processing place: {place}")
        places.append(list(place.keys())[0])
        attraction_map[list(place.keys())[0]] = list(place.values())[0]
    print(f"Places to map: {places}")
    locations = map_geo_info_with_region_check(places, google_map_key="AIzaSyD8kz0EW1KKo8B3I8GU7nAy19R8S6X6RVE", level='city', request_timeout=2000, total_timeout=10000)

    images = get_place_images(places, serpapi_key = "db19dc591d5a29e757aa20941de133cfe4d58630b1da017f898b436877b51389", real_search = image_search)
    ratings = get_llm_ratings(places)
    free_charge = get_llm_free_charge(places)

    print(f"Locations after mapping: {locations}")
    clusters = cluster_close_locations(locations, eps_km=50)
    print(f"Clusters formed: {clusters}")
    new_clusters = {}
    for key, old_list in clusters.items():
        print(f"Processing cluster {key} with {len(old_list)} items")
        new_list = []
        for item in old_list:
            print(f"Processing item: {item}")
            new_item = {}
            new_item['name'] = item['name']
            new_item['latitude'] = item['latitude']
            new_item['longitude'] = item['longitude']
            new_item['image'] = images.get(item['name'], ["https://www.example.com/default_image_2.jpg"])
            new_item['rating'] = ratings.get(item['name'], 0)
            new_item['free'] = free_charge.get(item['name'], False)
            print(f"Mapping name to description: {new_item['name']}")
            new_item['description'] = attraction_map[new_item['name']]
            print(f"New item: {new_item}")
            new_list.append(new_item)
        new_clusters[key] = new_list
    return new_clusters

@csrf_exempt
def show_lattest_longtitude_latitude(request):
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            conversation_id_str = body_data.get('conversation_id')
            user_id = body_data.get('user_id', -1)
            image_search_true = body_data.get('image_search', False)

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
            lattest_content = past_messages.last().content
            print(f"lattest content is {lattest_content}")
            print("calling show_lattest_longtitude_latitude")
            clusters = extract_clusters(lattest_content, "Extract the main tourist attractions mentioned in the following text with about 100 word description", image_search=image_search_true)
            return JsonResponse({
                "geo_info": clusters
                                })
        except Exception as e:
            return JsonResponse({"error": f"json decode error: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)
    





@csrf_exempt
def show_lattest_deepsearch_longtitude_latitude(request):
    print(f"calling show_lattest_deepsearch_longtitude_latitude")
    import json
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            conversation_id = body_data.get('conversation_id')
            image_search_true = body_data.get('image_search', False)
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
            clusters = extract_clusters(latest_llm_output, "Extract the main tourist attractions mentioned in the following text Itinerary Table section with about 100 word description.", image_search=image_search_true)
            
            return JsonResponse({
                "geo_info": clusters
            })

        except Exception as e:
            return JsonResponse({"error": f"Internal server error: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405) 
