from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from tool.llm_helper import basic_talk
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.core.cache import cache
from core.models import Conversation, Message
import json
import uuid
import re
import logging
from django.conf import settings

# Configure logging
logger = logging.getLogger(__name__)

def remove_emoji(text):
    # 使用 Unicode 区间匹配 emoji
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002700-\U000027BF"  # Dingbats
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002600-\U000026FF"  # Misc symbols
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text)

def validate_input(data):
    """Validate and sanitize input data"""
    if not isinstance(data, dict):
        return False, "Invalid data format"
    
    query = data.get('query', '').strip()
    if not query:
        return False, "Query cannot be empty"
    
    if len(query) > 10000:  # Reasonable limit
        return False, "Query too long"
    
    # Basic XSS protection
    dangerous_patterns = ['<script', 'javascript:', 'onclick=', 'onerror=']
    query_lower = query.lower()
    for pattern in dangerous_patterns:
        if pattern in query_lower:
            return False, "Invalid content detected"
    
    return True, query

def check_rate_limit(request):
    """Simple rate limiting based on IP address"""
    if settings.DEBUG:
        return True  # Skip rate limiting in debug mode
    
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR')
    if client_ip:
        client_ip = client_ip.split(',')[0].strip()
    else:
        client_ip = request.META.get('REMOTE_ADDR', 'unknown')
    
    cache_key = f"rate_limit_{client_ip}"
    request_count = cache.get(cache_key, 0)
    
    if request_count >= 10:  # 10 requests per minute
        return False
    
    cache.set(cache_key, request_count + 1, 60)  # 60 seconds
    return True

@require_http_methods(["POST"])
@never_cache
@csrf_exempt  # TODO: Implement proper CSRF handling for API
def llm_talk(request):
    try:
        # Rate limiting
        if not check_rate_limit(request):
            logger.warning(f"Rate limit exceeded for IP: {request.META.get('REMOTE_ADDR')}")
            return JsonResponse({"error": "Rate limit exceeded. Please try again later."}, status=429)
        
        # Parse request body
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            logger.warning(f"Invalid request body: {e}")
            return JsonResponse({"error": "Invalid request format"}, status=400)
        
        # Validate input
        is_valid, result = validate_input(body_data)
        if not is_valid:
            logger.warning(f"Input validation failed: {result}")
            return JsonResponse({"error": result}, status=400)
        
        user_query = result
        conversation_id_str = body_data.get('conversation_id')

        # 判断是否已有对话
        if conversation_id_str:
            logger.info(f"Processing existing conversation {conversation_id_str}")
            try:
                conversation_id = int(conversation_id_str)
                conversation = Conversation.objects.get(id=conversation_id)
            except (Conversation.DoesNotExist, ValueError):
                try:
                    conversation_id = int(conversation_id_str)
                    conversation = Conversation(id=conversation_id)
                    conversation.save(force_insert=True)  # 强行指定主键插入
                except (ValueError, Exception) as e:
                    logger.error(f"Failed to create conversation: {e}")
                    return JsonResponse({"error": "Invalid conversation_id"}, status=400)
        else:
            logger.info("Creating new conversation")
            conversation = Conversation.objects.create()

        # 获取已有上下文 (limit to prevent excessive memory usage)
        past_messages = Message.objects.filter(
            conversation=conversation
        ).order_by('index')[:50]  # Limit context history
        
        history = [{"role": m.role, "content": m.content} for m in past_messages]
        history.append({"role": "user", "content": user_query})
        logger.info(f"Processing conversation with {len(history)} messages")

        try:
            assistant_reply = basic_talk(history)
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return JsonResponse({"error": "Service temporarily unavailable"}, status=503)

        # Save messages to database
        next_index = past_messages.count()
        try:
            Message.objects.create(
                conversation=conversation, 
                role='user', 
                content=user_query[:5000],  # Limit stored content length
                index=next_index
            )
            Message.objects.create(
                conversation=conversation, 
                role='assistant', 
                content=remove_emoji(assistant_reply)[:5000],  # Limit stored content length
                index=next_index + 1
            )
        except Exception as e:
            logger.error(f"Failed to save messages: {e}")
            # Still return the response even if saving failed
        
        return JsonResponse({
            "llm_content": assistant_reply,
            "conversation_id": str(conversation.id)
        })

    except Exception as e:
        logger.error(f"Unexpected error in llm_talk: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)

def index(request):
    return HttpResponse("Hello from core.index!")

@require_http_methods(["GET"])
def llm_talk_testing(request):
    """Testing endpoint with basic security"""
    if not settings.DEBUG:
        return JsonResponse({"error": "Testing endpoint disabled in production"}, status=404)
    
    logger.info("Testing LLM functionality")
    try:
        result = basic_talk([{"role":"user","content": "testing"}])
        return JsonResponse({"llm_content": result})
    except Exception as e:
        logger.error(f"Testing endpoint failed: {e}")
        return JsonResponse({"error": "Testing failed"}, status=500)