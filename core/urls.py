from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('llm_talk', views.llm_talk, name='llm_talk'),
    path('llm_talk_testing', views.llm_talk_testing, name='llm_talk_testing'),
    path('get_conversation_content', views.get_conversation_content, name = 'get_conversation_content'),
    path('get_conversation_content_by_id', views.get_conversation_content_by_id, name = 'get_conversation_content_by_id'),
    path('get_user_conversation_ids', views.get_user_conversation_ids, name = "get_user_conversation_ids"),
    path('create_user', views.create_user, name = 'create_user'),
    path('user_login', views.user_login, name = 'user_login'),
    path('make_post', views.make_post, name = 'make_post'),
    path('get_total_post_by_user_id', views.get_total_post_by_user_id, name = 'get_total_post_by_user_id'),
    path('like_post', views.like_post, name = 'like_post'),
    path('dislike_post', views.dislike_post, name = 'dislike_post'),
    path('get_all_post', views.get_all_post, name = 'get_all_post'),
    path('show_lattest_longtitude_latitude', views.show_lattest_longtitude_latitude, name = 'show_lattest_longtitude_latitude'),
    path('answer_deepsearch', views.answer_deepsearch, name = 'answer_deepsearch'),
]
