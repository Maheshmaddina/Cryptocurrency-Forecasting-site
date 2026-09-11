"""
Main URL configuration for CryptoSight project

Routes:
- /admin/ - Django admin interface
- / - Homepage and landing page
- /auth/ - User authentication (login, signup, profile)
- /predict/ - Cryptocurrency price prediction features
- /chat/ - AI-powered cryptocurrency assistant
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    path('auth/', include('authuser.urls')),
    path('predict/', include('predict.urls')),
    path('chat/', include(('chatbot.urls', 'chatbot'), namespace='chatbot')),
]

# Serve media files in development mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
