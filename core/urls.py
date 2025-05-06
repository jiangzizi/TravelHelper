from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('llm_talk', views.llm_talk, name='llm_talk'),
    path('llm_talk_testing', views.llm_talk_testing, name='llm_talk_testing'),
]
