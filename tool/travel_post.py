from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from core.models import OpenPost, User


@csrf_exempt
@require_http_methods(["POST"])
def make_post(request):
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        post_title = data.get("post_title")
        post_content = data.get("post_content")
        travel_place = data.get("travel_place", "")  # 可选字段，默认为空字符串
        if not all([user_id, post_title, post_content, travel_place]):
            return JsonResponse({"error": "Missing fields"}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

        post = OpenPost.objects.create(
            post_owner_name=user.name,
            post_title=post_title,
            post_content=post_content,
            travel_place=travel_place,
            like_list=[]  # 初始化为空
        )

        return JsonResponse({
            "message": "Post created successfully",
            "post_id": post.id
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

def get_total_post_by_user_id(request):
    if request.method == 'GET':
        try:
            user_id = request.GET.get('user_id')
            if not user_id:
                return JsonResponse({"error": "user_id is required"}, status=400)
    
            # 获取用户
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

            # 获取用户的所有帖子
            posts = OpenPost.objects.filter(post_owner_name=user.name)
            post_list = [{"post_id": post.id, "post_title": post.post_title, 
                          "travel_place": post.travel_place,
                          "post_content": post.post_content, "like_list": post.like_list} for post in posts]
            total_posts = len(post_list)
            return JsonResponse({
                "total_posts": total_posts,
                "posts": post_list
            }, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        


@csrf_exempt
@require_http_methods(["POST"])
def like_post(request):
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        post_id = data.get("post_id")

        if not all([user_id, post_id]):
            return JsonResponse({"error": "user_id and post_id are required"}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

        try:
            post = OpenPost.objects.get(id=post_id)
        except OpenPost.DoesNotExist:
            return JsonResponse({"error": "Post not found"}, status=404)

        # 确保 like_list 是一个 list，并避免重复点赞
        if user.name not in post.like_list:
            post.like_list.append(user.name)
            post.save()

        return JsonResponse({
            "message": "Post liked successfully",
            "like_list": post.like_list
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def dislike_post(request):
    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        post_id = data.get("post_id")

        if not all([user_id, post_id]):
            return JsonResponse({"error": "user_id and post_id are required"}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

        try:
            post = OpenPost.objects.get(id=post_id)
        except OpenPost.DoesNotExist:
            return JsonResponse({"error": "Post not found"}, status=404)

        # 如果用户名在 like_list 中就移除
        if user.name in post.like_list:
            post.like_list.remove(user.name)
            post.save()

        return JsonResponse({
            "message": "Post disliked successfully",
            "like_list": post.like_list
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


from django.views.decorators.http import require_GET

@require_GET
def get_all_post(request):
    try:
        # 随机排序并限制最多100条
        posts = OpenPost.objects.order_by('?')[:100]
        post_list = [{
            "post_id": post.id,
            "post_owner_name": post.post_owner_name,
            "post_title": post.post_title,
            "post_content": post.post_content,
            "travel_place": post.travel_place,
            "like_list": post.like_list
        } for post in posts]

        return JsonResponse({
            "total_returned": len(post_list),
            "posts": post_list
        }, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
