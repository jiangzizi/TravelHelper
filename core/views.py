from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Conversation, Message
from zhipuai import ZhipuAI
from praisonaiagents import Agent, Agents, MCP
import os, re, json
from tool.map import *
from tool.simple import *
from tool.conversation import *
from tool.user import *
from tool.travel_post import *

def keep_after_last_function_tag(s):
    match = re.search(r'</function>(.*)$', s, re.DOTALL)
    return match.group(1) if match else s

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
    agents = Agents(agents=[general_search_agent])
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



def generate_final_response(message_list, search_results=None):
    print(f"message list for final generation {message_list}")
    """Generates final reply, yielding chunks if streaming."""
    client = ZhipuAI(api_key="0982eaa8f53f4d649e003336000451c5.E5OuhWgc7pAtHeJf") # Use your actual key or env var
    
    print(f"Search result for final generation (raw): {search_results}")
    processed_search_results = keep_after_last_function_tag(search_results) if search_results else None
    print(f"Search result for final generation (processed): {processed_search_results}")
    
    system_prompt = {
        "role": "system",
        "content": "You are a helpful travel assistant. You can only answer travel related questions."
    }
    
    messages = [system_prompt]
    # Ensure message_list is a list of dictionaries
    if isinstance(message_list, list) and all(isinstance(item, dict) for item in message_list):
        messages.extend(message_list)
    else:
        print(f"Warning: message_list is not in the expected format: {message_list}")
        # Potentially handle this error or provide a default
        # For now, let's assume it might be a single message if not a list.
        if isinstance(message_list, dict):
             messages.append(message_list)


    # Make sure there's at least one user/assistant message to append search results to
    if not messages or messages[-1]["role"] == "system":
        # Add a dummy user message if history is empty or ends with system,
        # so search results can be appended to a user/assistant message.
        # This might need refinement based on your actual message flow.
        # Or, if the last message_list item is the user query, use that.
        # Let's assume message_list always ends with the latest user query if it's not empty.
        if message_list and message_list[-1]["role"] == "user":
            # The last message in message_list is the current user query
             # The content will be updated below
            pass
        else:
            # This case should ideally not happen if message_list is properly constructed
            print("Warning: Cannot append search results as no suitable message found.")


    if processed_search_results:
        # Append to the content of the last message, which should be the user's query
        if messages and messages[-1].get("content") is not None:
            messages[-1]["content"] += f"\n\nAnswer my question based on the following information:\n{processed_search_results}\n"
        else:
            # This is a fallback, ideally the message structure should ensure a content field exists
            messages.append({"role": "user", "content": f"Based on this info: {processed_search_results}, answer."})


    print(f"Messages for final generation: {messages}")
    
    try:
        print(f"histroy for final generation {messages}")
        stream = client.chat.completions.create(
            model="glm-4-flash",
            messages=messages,
            stream=True,
            # max_tokens can be set if you want to limit output, but for streaming,
            # it's often better to let the model decide when to stop or handle it client-side.
        )
        for chunk in stream:
            if chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        print(f"Error during ZhipuAI stream: {e}")
        yield f"An error occurred while generating the response: {str(e)}" # Yield an error message

def smart_talk(message_list, basic=True):
    """
    Intelligent conversation flow, supporting streaming.
    Yields:
        - A dictionary with 'type': 'metadata', 'search_result', 'longtitude_latitude'
        - Dictionaries with 'type': 'content_chunk', 'chunk': (text chunk)
        - Optionally, 'type': 'done' or 'type': 'error'
    """
    latest_user_message = next((msg for msg in reversed(message_list) if msg["role"] == "user"), None)

    if not latest_user_message:
        yield {"type": "content_chunk", "chunk": "Please提出您的问题。"}
        return

    user_query = latest_user_message["content"]
    
    search_result_data = "None"
    longtitude_latitude_data = "None"

    if basic:
        # Yield metadata first, even if it's "None"
        yield {
            "type": "metadata",
            "search_result": search_result_data,
            "longtitude_latitude": longtitude_latitude_data
        }
        # Then stream the direct answer
        for chunk in generate_final_response(message_list):
            yield {"type": "content_chunk", "chunk": chunk}
        return

    # --- Non-basic flow (with search) ---
    try:
        if should_search(message_list):
            search_result_data = perform_search(user_query)
            # Potentially, extract_longtitude_latitude could also fail
            try:
                longtitude_latitude_data = extract_longtitude_latitude(search_result_data)
            except Exception as e:
                print(f"Error extracting lat/long: {e}")
                longtitude_latitude_data = f"Error: {e}" # Or "None"

            # Yield metadata collected so far
            yield {
                "type": "metadata",
                "search_result": search_result_data, # Send the full search result string
                "longtitude_latitude": longtitude_latitude_data
            }
            # Stream the answer based on search results
            for chunk in generate_final_response(message_list, search_result_data):
                yield {"type": "content_chunk", "chunk": chunk}
        else:
            # No search needed, yield default metadata
            yield {
                "type": "metadata",
                "search_result": "None", # Explicitly "None"
                "longtitude_latitude": "None" # Explicitly "None"
            }
            # Stream the direct answer without search
            for chunk in generate_final_response(message_list):
                yield {"type": "content_chunk", "chunk": chunk}
        
        yield {"type": "done"} # Signal completion

    except Exception as e:
        print(f"Error in smart_talk's main logic: {e}")
        # Yield metadata with error if available, or defaults
        yield {
            "type": "metadata",
            "search_result": search_result_data if search_result_data != "None" else f"Error occurred before search: {e}",
            "longtitude_latitude": longtitude_latitude_data if longtitude_latitude_data != "None" else "Error"
        }
        # Yield an error message chunk
        yield {"type": "error", "message": f"An error occurred: {str(e)}"}


@csrf_exempt
def llm_talk(request):
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            user_query = body_data.get('query', '')
            conversation_id_str = body_data.get('conversation_id')
            user_id = body_data.get('user_id', -1)

            if not user_query:
                return JsonResponse({"error": "Query cannot be empty"}, status=400)
            # ... (rest of your conversation and user validation) ...
            
            # Example of conversation handling (adapt to your actual model usage)
            conversation = None
            if conversation_id_str:
                try:
                    conversation_id = int(conversation_id_str)
                    conversation = Conversation.objects.get(id=conversation_id)
                    if conversation.user_id != user_id:
                        return JsonResponse({"error": "User ID does not match the conversation"}, status=403)
                except ValueError:
                    return JsonResponse({"error": "Invalid conversation_id format"}, status=400)
                except Conversation.DoesNotExist:
                    conversation = Conversation.objects.create(user_id=user_id, id = conversation_id) # Or handle as error
            else:
                conversation = Conversation.objects.create(user_id=user_id)
            
            print(f"Conversation ID: {conversation.id}, User ID: {user_id}")

            past_messages_qs = Message.objects.filter(conversation=conversation).order_by('index')
            history = [{"role": m.role, "content": m.content} for m in past_messages_qs]
            
            next_index = past_messages_qs.count()
            Message.objects.create(conversation=conversation, role='user', content=user_query, index=next_index)
            
            history.append({"role": "user", "content": user_query})

            # --- THIS IS THE STREAMING PART ---
            def stream_response_generator():
                full_assistant_reply_parts = []
                # These will be populated by the 'metadata' event from smart_talk
                search_result_for_db = "None" 
                longtitude_latitude_for_db = "None"

                try:
                    # smart_talk IS A GENERATOR. We iterate over the dicts it yields.
                    for item in smart_talk(history, basic=False): # 'item' will be a dictionary
                        if not isinstance(item, dict):
                            print(f"Warning: smart_talk yielded non-dict item: {item}")
                            # Handle this unexpected case, maybe yield an error event
                            error_payload = {"type": "error", "message": f"Internal server error: unexpected stream item format."}
                            yield f"data: {json.dumps(error_payload)}\n\n"
                            continue # or break

                        # Now it's safe to use .get() on 'item'
                        item_type = item.get("type")

                        if item_type == "metadata":
                            search_result_for_db = item.get("search_result", "None")
                            longtitude_latitude_for_db = item.get("longtitude_latitude", "None")
                            # Send metadata to client
                            yield f"data: {json.dumps(item)}\n\n"
                        elif item_type == "content_chunk":
                            chunk_text = item.get("chunk", "")
                            full_assistant_reply_parts.append(chunk_text)
                            # Send content chunk to client
                            yield f"data: {json.dumps(item)}\n\n"
                        elif item_type == "error":
                            yield f"data: {json.dumps(item)}\n\n"
                        elif item_type == "done":
                            yield f"data: {json.dumps(item)}\n\n"
                        else:
                            print(f"Warning: Unknown item type from smart_talk: {item_type}")
                            # Optionally yield an event for unknown types too

                    # After the loop, save the full assembled reply
                    assistant_final_reply = "".join(full_assistant_reply_parts)
                    if assistant_final_reply: # Only save if there's content
                        Message.objects.create(
                            conversation=conversation,
                            role='assistant',
                            content=assistant_final_reply,
                            index=next_index + 1
                        )
                        # You could also update the conversation object here with
                        # search_result_for_db and longtitude_latitude_for_db if needed
                        print(f"Assistant reply saved. Length: {len(assistant_final_reply)}")
                    else:
                        print("No assistant reply content to save.")

                except Exception as e:
                    print(f"Error during smart_talk stream generation: {e}")
                    import traceback
                    traceback.print_exc()
                    error_payload = {"type": "error", "message": f"Server error during streaming: {str(e)}"}
                    yield f"data: {json.dumps(error_payload)}\n\n"
                finally:
                    print("Stream generation process finished or errored.")
                    # A final "stream_end" event can be useful for clients
                    # yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"


            response = StreamingHttpResponse(stream_response_generator(), content_type="text/event-stream")
            response['Cache-Control'] = 'no-cache'
            return response

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
        except Exception as e:
            print(f"Unhandled error in llm_talk view: {e}")
            import traceback
            traceback.print_exc() # This will print the full traceback to your server console
            return JsonResponse({"error": f"An unexpected server error occurred: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

@csrf_exempt
def index(request):
    return HttpResponse("Hello from core.index!")

