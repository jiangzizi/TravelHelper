from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from tool.llm_helper import basic_talk
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt  # 开发阶段为了方便关闭 CSRF 检查，生产建议改成认证方式处理
def llm_talk(request):
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            user_query = body_data.get('query', '')
            print("Received user query:", user_query)

            # 调用你的处理函数
            result = basic_talk(user_query)
            return JsonResponse({"llm_content": result})
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)


def index(request):
    return HttpResponse("Hello from core.index!")

def llm_talk_testing(request):
    print("calling llm talk")
    return JsonResponse({"llm_content": basic_talk("testing")})