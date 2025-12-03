from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


admin.site.site_header = "FINANCE TRACKER ADMIN"
admin.site.site_title = "Finance Tracker Admin"
admin.site.index_title = "Welcome to your dashboard"

urlpatterns = [
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # API v1 endpoints
    path('api/v1/auth/', include('apps.users.urls')),
    path('api/v1/', include('apps.categories.urls')),
    path('api/v1/', include('apps.accounts.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
