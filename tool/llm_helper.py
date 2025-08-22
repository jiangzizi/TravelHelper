from zhipuai import ZhipuAI
from pathlib import Path
import json, requests
import os
import logging

logger = logging.getLogger(__name__)

def basic_talk(message_list):
    """
    Secure LLM API call with proper error handling and validation
    """
    # Validate input
    if not message_list or not isinstance(message_list, list):
        raise ValueError("Invalid message list provided")
    
    # Check for required API key
    soa_key = os.getenv("SOA_KEY")
    if not soa_key:
        logger.error("SOA_KEY environment variable not set")
        raise ValueError("API key not configured")
    
    # Prepare system prompt and messages
    system_prompt = {"role": "system",
                     "content": "You are a helpful travel assistant. Please provide safe and accurate travel information."}
    
    # Validate and sanitize messages
    validated_messages = []
    for msg in message_list:
        if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
            continue
        
        role = str(msg['role']).strip()
        content = str(msg['content']).strip()
        
        # Limit content length to prevent abuse
        if len(content) > 5000:
            content = content[:5000] + "... (truncated)"
        
        if role in ['user', 'assistant', 'system'] and content:
            validated_messages.append({"role": role, "content": content})
    
    if not validated_messages:
        raise ValueError("No valid messages to process")
    
    messages = [system_prompt] + validated_messages

    try:
        from openai import OpenAI
        
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=soa_key,
        )

        completion = client.chat.completions.create(
            extra_headers={
                # Optional. Site URL for rankings on openrouter.ai.
                "HTTP-Referer": "https://travelhelper.app",
                # Optional. Site title for rankings on openrouter.ai.
                "X-Title": "TravelHelper",
            },
            model="deepseek/deepseek-chat-v3-0324:free",
            messages=messages,
            max_tokens=2000,  # Limit response length
            temperature=0.7,
            timeout=30  # 30 second timeout
        )
        
        response_content = completion.choices[0].message.content
        logger.info(f"LLM API call successful, response length: {len(response_content)}")
        
        return response_content
        
    except Exception as e:
        logger.error(f"LLM API call failed: {str(e)}")
        raise Exception("Failed to get response from AI service")
