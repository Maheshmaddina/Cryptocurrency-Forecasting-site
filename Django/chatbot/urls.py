from django.urls import path
from . import views

urlpatterns = [
    # The main endpoint for chatbot communication
    path('', views.chatbot_response, name='chatbot_response'),
]