"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# backend/config/urls.py

from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('apps.accounts.urls')),
    path('api/exchanges/', include('apps.exchanges.urls')),
    path('api/instruments/', include('apps.instruments.urls')),
    path('api/strategies/', include('apps.strategies.urls')),
    path('api/bots/', include('apps.bots.urls')),
    path('api/trading/', include('apps.trading.urls')),
    path('api/risk/', include('apps.risk.urls')),
    path('api/signals/', include('apps.signals.urls')),
    path('api/agents/', include('apps.agents.urls')),
    path('api/agent-runtime/', include('apps.agent_runtime.urls')),
    path('api/logging/', include('apps.logging_app.urls')),
    path('api/connectors/', include('apps.connectors.urls')),
    path('api/market-data/', include('apps.market_data.urls')),
    path('api/backtesting/', include('apps.backtesting.urls')),
]
