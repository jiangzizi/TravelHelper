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
]
