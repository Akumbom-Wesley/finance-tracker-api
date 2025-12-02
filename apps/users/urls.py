from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView,
    LogoutView,
    UserProfileView,
    health_check,
)

urlpatterns = [
    # Health check
    path('health/', health_check, name='health-check'),

    # JWT Authentication
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # Djoser endpoints (registration, user management, password reset)
    path('', include('djoser.urls')),
    # This gives us /users/, /users/me/, /users/set_password/, /users/reset_password/, etc.

    # Custom profile endpoint (more specific than Djoser's /users/me/)
    path('profile/', UserProfileView.as_view(), name='user-profile'),
]
