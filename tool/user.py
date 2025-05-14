import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from core.models import User, Conversation

# 创建用户
@csrf_exempt
def create_user(request):
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            name = body_data.get('name', '')
            password = body_data.get('password', '')

            if not name or not password:
                return JsonResponse({"error": "name and password are required"}, status=400)

            # 创建用户
            try:
                user = User.objects.create(name=name, password=password)
            except IntegrityError:
                return JsonResponse({"error": "Username already exists"}, status=400)

            # 获取当前最大的 conversation_id
            max_conversation_id = Conversation.objects.all().order_by('-id').first()
            max_conversation_id = max_conversation_id.id if max_conversation_id else None

            return JsonResponse({
                "user_id": user.id,
                "max_conversation_id": max_conversation_id
            })

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)


# 用户登录
@csrf_exempt
def user_login(request):
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            name = body_data.get('name', '')
            password = body_data.get('password', '')

            if not name or not password:
                return JsonResponse({"error": "name and password are required"}, status=400)

            # 查找用户
            try:
                user = User.objects.get(name=name)
            except User.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

            # 密码验证
            if password == user.password:
                # 获取当前最大的 conversation_id
                max_conversation_id = Conversation.objects.all().order_by('-id').first()
                max_conversation_id = max_conversation_id.id if max_conversation_id else None

                return JsonResponse({
                    "user_id": user.id,
                    "max_conversation_id": max_conversation_id
                })
            else:
                return JsonResponse({"error": "Incorrect password"}, status=403)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)
