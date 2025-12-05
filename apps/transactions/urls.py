from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet, TagViewSet

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'tags', TagViewSet, basename='tag')

urlpatterns = [
    path('', include(router.urls)),
]
