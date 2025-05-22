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

# Helper function (already provided)
def keep_after_last_function_tag(s):
    match = re.search(r'</function>(.*)$', s, re.DOTALL)
    return match.group(1) if match else s

# --- LLM Interaction Functions ---

def should_search(message_list):
    """判断是否需要搜索"""
    client = ZhipuAI(api_key="0982eaa8f53f4d649e003336000451c5.E5OuhWgc7pAtHeJf")
    system_prompt = {
        "role": "system",
        "content": """Decide whether you need to call web search function to answer user's query. Only output 'YES' or 'NO'.
        Output 'YES' if user ask for weather, directions, local food, detailed travel planing, longitude or latitude search.
        """
    }
    messages = [system_prompt]
    if message_list: # Ensure message_list is not empty
        messages.append(message_list[-1]) # Use the last message (current user query)
    else: # Should not happen if history includes user query
        return False # Default to NO if no user query found

    print(f"should_search messages: {messages}")
    try:
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=messages,
            max_tokens=10
        )
        decision = response.choices[0].message.content.strip().upper()
        print(f"Search decision from LLM: {decision}")
        return decision == "YES"
    except Exception as e:
        print(f"Error in should_search: {e}")
        return False # Default to NO on error

def perform_search(query):
    print(f"Performing search for query: '{query}'")
    """执行搜索"""
    brave_api_key = "BSAzbNViPbppE07cSHaKYV8dkcgCzz0"
    os.environ["BRAVE_API_KEY"] = brave_api_key
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")

    # General Search Agent
    # Make sure MCP path is correct or it's globally available.
    # If npx isn't in PATH for the Django process, this could fail.
    # Consider using a Python library for Brave search directly if praisonaiagents has issues in Django.
    from praisonaiagents import Agent, Agents, MCP # Assuming this is correctly set up
    try:
        general_search_agent = Agent(
            role="Web Searcher", # Added role for clarity
            goal=f"Perform general web searches to gather information for the query: {query}", # Added goal
            instructions="Perform general web searches to gather information relevant to the user's query. Return concise and relevant search snippets or summaries.",
            # llm="groq/llama3-8b-8192", # Example, adjust as needed; smaller/faster model might be better
            llm="groq/meta-llama/llama-4-scout-17b-16e-instruct", # Original
            tools=[MCP("npx -y @modelcontextprotocol/server-brave-search", env={"BRAVE_API_KEY": brave_api_key})]
        )
        agents = Agents(agents=[general_search_agent])
        result = agents.start(f"Search the web for information related to: {query}", return_dict = True) # Make the task very explicit
        print(f"Raw search result from praisonai: {result}")
        return result["task_results"][0].raw
    except Exception as e:
        print(f"Error during perform_search with praisonaiagents: {e}")
        # Fallback or simpler search mechanism can be added here
        return f"Error performing search: {e}"


def extract_longtitude_latitude(text_to_search_in):
    print(f"Extracting lat/long from: '{text_to_search_in[:200]}...'") # Log snippet
    client = ZhipuAI(api_key="0982eaa8f53f4d649e003336000451c5.E5OuhWgc7pAtHeJf")
    system_prompt = {
        "role": "system",
        "content": """Extract longitude and latitude from the provided text. If no valid longitude and latitude are found, output only the word 'None'.
        Otherwise, output only the longitude and latitude in the format of '[longitude,latitude]', e.g., '[116.4074,39.9042]'.
        Strictly follow the format. DO NOT add any other content, reasoning, or explanations.
        """
    }
    messages = [
        system_prompt,
        {"role": "user", "content": f"Extract longitude and latitude from the following text:\n\n{text_to_search_in}"}
    ]
    try:
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=messages,
            max_tokens=50 # Increased slightly for safety, but should be short
        )
        output = response.choices[0].message.content.strip() # No .upper() needed here
        print(f"Lat/long extraction output: {output}")
        # Validate format roughly
        if re.match(r'^\[-?\d+(\.\d+)?,-?\d+(\.\d+)?\]$', output) or output.upper() == "NONE":
            return output
        else:
            print(f"Warning: Lat/long extraction returned unexpected format: {output}. Defaulting to 'None'.")
            return "None" # Default to "None" if format is off
    except Exception as e:
        print(f"Error in extract_longtitude_latitude: {e}")
        return "None" # Default to "None" on error

def generate_final_response(message_list, search_results_for_llm=None):
    print(f"Generating final response. Message list length: {len(message_list)}")
    client = ZhipuAI(api_key="0982eaa8f53f4d649e003336000451c5.E5OuhWgc7pAtHeJf")
    
    processed_search_results = keep_after_last_function_tag(search_results_for_llm) if search_results_for_llm else None
    
    system_prompt_content = "You are a helpful travel assistant. You can only answer travel related questions."
    if processed_search_results:
        system_prompt_content += f"\n\nUse the following information to answer the user's LATEST query if it is relevant. Do not mention that you are using this information unless it's crucial for context. Focus on the user's direct question.\nInformation:\n{processed_search_results}"

    system_prompt = {"role": "system", "content": system_prompt_content}
    
    messages_for_llm = [system_prompt]
    
    # Add historical messages, ensuring not to duplicate system prompt or add empty user message
    if isinstance(message_list, list):
        messages_for_llm.extend([msg for msg in message_list if msg.get("content")]) # Filter out potential empty messages
    
    if not any(msg["role"] == "user" for msg in messages_for_llm):
         # This case should be rare if message_list is correctly populated with user query
        print("Warning: No user message found in messages_for_llm for final generation.")
        yield "I need a user question to respond to."
        return

    print(f"Messages for final ZhipuAI generation: {json.dumps(messages_for_llm, indent=2)}")
    
    try:
        stream = client.chat.completions.create(
            model="glm-4-flash",
            messages=messages_for_llm,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        print(f"Error during ZhipuAI stream for final response: {e}")
        yield f"An error occurred while generating the response: {str(e)}"

# --- Main Orchestration Logic ---

def smart_talk(message_list, basic=False):
    """
    Intelligent conversation flow, yielding dictionaries for streaming.
    Types of yielded events:
    - {"type": "status", "message": "..."}
    - {"type": "search_decision", "decision": "YES" | "NO"}
    - {"type": "intermediate_result", "source": "perform_search" | "extract_longtitude_latitude", "content": "..."}
    - {"type": "llm_chunk", "chunk": "..."}
    - {"type": "error", "source": "...", "message": "..."}
    - {"type": "done"}
    """
    latest_user_message = next((msg for msg in reversed(message_list) if msg["role"] == "user"), None)

    if not latest_user_message:
        yield {"type": "error", "source": "smart_talk_setup", "message": "No user query found in message history."}
        yield {"type": "llm_chunk", "chunk": "Please provide your question."} # Send a fallback message
        yield {"type": "done"}
        return

    user_query = latest_user_message["content"]
    
    # These will store the actual data to be used/saved
    search_data_for_llm = None
    final_search_result_for_db = "None"
    final_long_lat_for_db = "None"

    if basic:
        yield {"type": "status", "message": "Basic mode: Skipping search and location extraction."}
        # Fallthrough to generate_final_response with no search data
    else:
        # Non-basic flow
        try:
            search_needed = should_search(message_list)
            yield {"type": "search_decision", "decision": "YES" if search_needed else "NO"}

            if search_needed:
                yield {"type": "status", "message": "Performing web search..."}
                raw_search_output = perform_search(user_query)
                final_search_result_for_db = raw_search_output # Store for DB
                search_data_for_llm = raw_search_output     # Store for LLM input
                yield {"type": "intermediate_result", "source": "perform_search", "content": raw_search_output}
                
                yield {"type": "status", "message": "Extracting longitude and latitude..."}
                # Use raw_search_output as context for extraction, or user_query if more appropriate
                # The original code used search_result_data (output of perform_search)
                extracted_location = extract_longtitude_latitude(raw_search_output if raw_search_output else user_query)
                final_long_lat_for_db = extracted_location # Store for DB
                yield {"type": "intermediate_result", "source": "extract_longtitude_latitude", "content": extracted_location}
                # Note: extracted_location is not directly passed to generate_final_response in this setup,
                # but it's available if the LLM prompt is modified to use it.
            else:
                yield {"type": "status", "message": "Search not required for this query."}
        
        except Exception as e:
            err_msg = f"Error during search/geolocation phase: {str(e)}"
            print(err_msg)
            yield {"type": "error", "source": "search_processing", "message": err_msg}
            # Continue, but search_data_for_llm will be None or potentially an error string
            if search_data_for_llm is None:
                 search_data_for_llm = f"Note: An error occurred during information retrieval: {e}"


    # This is a conceptual placeholder for where you'd save to DB if not at the very end.
    # In the current llm_talk, it's saved after all LLM chunks are collected.
    # We'll pass these to llm_talk to save later.
    yield {
        "type": "processing_metadata_for_saving", # Special event type for llm_talk to capture these
        "db_search_result": final_search_result_for_db,
        "db_long_lat": final_long_lat_for_db
    }

    yield {"type": "status", "message": "Generating final assistant response..."}
    for chunk in generate_final_response(message_list, search_data_for_llm):
        yield {"type": "llm_chunk", "chunk": chunk}
    
    yield {"type": "done"}


# --- Django View ---

@csrf_exempt
def llm_talk(request):
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            user_query = body_data.get('query', '')
            conversation_id_str = body_data.get('conversation_id')
            user_id = body_data.get('user_id', -1) # Default to -1 or handle as error if not provided

            if not user_query:
                return JsonResponse({"error": "Query cannot be empty"}, status=400)
            if user_id == -1: # Or however you validate user_id
                 return JsonResponse({"error": "User ID is required"}, status=400)


            conversation = None
            if conversation_id_str:
                try:
                    conversation_id = int(conversation_id_str)
                    conversation = Conversation.objects.get(id=conversation_id)
                    if conversation.user_id != user_id: # Ensure user owns the conversation
                        # For robust multi-user, user_id should come from authenticated session
                        return JsonResponse({"error": "User ID does not match the conversation owner"}, status=403)
                except ValueError:
                    return JsonResponse({"error": "Invalid conversation_id format"}, status=400)
                except Conversation.DoesNotExist:
                    # Option 1: Create if not exists (as in original code, but ensure ID consistency)
                    # If client sends an ID that doesn't exist, it might be an attempt to resume.
                    # Creating it might be unexpected if the ID was from a deleted convo.
                    # For now, let's assume if ID is provided, it *should* exist, or it's an error.
                    # return JsonResponse({"error": "Conversation with provided ID not found"}, status=404)
                    # OR, create it (as per original, but be careful with ID assignment if client provides it)
                    print(f"Conversation ID {conversation_id_str} not found. Creating new one for user {user_id} with this ID.")
                    conversation = Conversation.objects.create(user_id=user_id, id=conversation_id)
            else: # No conversation_id provided, create a new one
                conversation = Conversation.objects.create(user_id=user_id)
            
            print(f"Using Conversation ID: {conversation.id}, User ID: {user_id}")

            past_messages_qs = Message.objects.filter(conversation=conversation).order_by('index')
            history = [{"role": m.role, "content": m.content} for m in past_messages_qs]
            
            next_index = past_messages_qs.count() # Index for the new user message
            Message.objects.create(conversation=conversation, role='user', content=user_query, index=next_index)
            
            history.append({"role": "user", "content": user_query}) # Add current query to history for smart_talk

            # --- STREAMING RESPONSE ---
            def stream_response_generator():
                full_assistant_reply_parts = []
                # These will be populated by the 'processing_metadata_for_saving' event
                captured_search_result_for_db = "None"
                captured_long_lat_for_db = "None"

                try:
                    # smart_talk is the generator yielding various event types
                    for item in smart_talk(history, basic=False): # Set basic=True for testing w/o search
                        item_type = item.get("type")

                        if item_type == "llm_chunk":
                            chunk_text = item.get("chunk", "")
                            full_assistant_reply_parts.append(chunk_text)
                            # Stream this chunk to the client
                            yield f"data: {json.dumps(item)}\n\n"
                        elif item_type == "processing_metadata_for_saving":
                            # This event is for capturing data meant for DB, not directly for client display usually
                            # But we can still send it if client wants to know
                            captured_search_result_for_db = item.get("db_search_result", "None")
                            captured_long_lat_for_db = item.get("db_long_lat", "None")
                            print(f"Captured for DB: Search='{str(captured_search_result_for_db)[:100]}...', LatLng='{captured_long_lat_for_db}'")
                            # Optionally stream this metadata if client needs it for some reason
                            # yield f"data: {json.dumps(item)}\n\n" 
                            # For now, let's assume client mainly cares about other events.
                        else: # For "status", "intermediate_result", "error", "done", "search_decision"
                            # Stream these events directly to the client
                            yield f"data: {json.dumps(item)}\n\n"
                        
                    # After the loop, all parts of the assistant's reply are collected
                    assistant_final_reply = "".join(full_assistant_reply_parts)

                    if assistant_final_reply:
                        print(f"Saving assistant reply. Length: {len(assistant_final_reply)}")
                        # Save the assistant's message
                        # If you want to save search_result and long_lat with the Message object,
                        # your Message model needs fields for them.
                        Message.objects.create(
                            conversation=conversation,
                            role='assistant',
                            content=assistant_final_reply,
                            index=next_index + 1 # Index for the assistant message
                            # search_context=captured_search_result_for_db, # If Message model has this field
                            # location_info=captured_long_lat_for_db,     # If Message model has this field
                        )
                        # Alternatively, update the Conversation object if these are per-turn summaries
                        # conversation.last_search_result = captured_search_result_for_db
                        # conversation.last_location_info = captured_long_lat_for_db
                        # conversation.save()
                    else:
                        print("No assistant reply content generated to save.")

                except Exception as e:
                    print(f"Error within stream_response_generator or smart_talk: {e}")
                    import traceback
                    traceback.print_exc()
                    error_payload = {"type": "error", "source": "stream_generator", "message": f"Server error during streaming: {str(e)}"}
                    yield f"data: {json.dumps(error_payload)}\n\n"
                finally:
                    print("Stream generation process finished or errored out.")
                    # Optionally send a specific final "stream_end" event if not relying on "done"
                    # yield f"data: {json.dumps({'type': 'stream_closed'})}\n\n"

            response = StreamingHttpResponse(stream_response_generator(), content_type="text/event-stream")
            response['Cache-Control'] = 'no-cache' # Important for SSE
            response['X-Accel-Buffering'] = 'no' # For Nginx, to disable buffering
            return response

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
        except Exception as e:
            print(f"Critical unhandled error in llm_talk view: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({"error": f"An unexpected server error occurred: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

import os

def deepsearch():
    from mypraisonaiagents import Agent, Agents, MCP
    brave_api_key = "BSAzbNViPbppE07cSHaKYV8dkcgCzz0"
    os.environ["BRAVE_API_KEY"] = brave_api_key


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

