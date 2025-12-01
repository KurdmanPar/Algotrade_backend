# apps/agent_runtime/urls.py
from django.urls import path
from . import views

# urlpatterns = [
#     path('agents/<int:agent_id>/start/', views.start_agent, name='start-agent'),
#     path('agents/<int:agent_id>/stop/', views.stop_agent, name='stop-agent'),
#     # سایر مسیرها...
# ]

urlpatterns = [
    path('agents/<int:agent_id>/start/', views.start_agent, name='start-agent'),
    path('agents/<int:agent_id>/stop/', views.stop_agent, name='stop-agent'),
    # سایر مسیرها...
]