from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from .models import Category
from .serializers import (
    CategorySerializer,
    CategoryListSerializer,
    CategoryDetailSerializer
)


@extend_schema_view(
    list=extend_schema(
        summary="List Categories",
        description="Get all categories (system defaults + user's custom categories)",
        parameters=[
            OpenApiParameter(
                name='type',
                description='Filter by type (income/expense)',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='search',
                description='Search in category name',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='is_active',
                description='Filter by active status',
                required=False,
                type=bool
            ),
        ]
    ),
    retrieve=extend_schema(
        summary="Get Category Details",
        description="Retrieve a specific category with transaction count and full details"
    ),
    create=extend_schema(
        summary="Create Custom Category",
        description="Create a new user-specific category. User is automatically assigned."
    ),
    update=extend_schema(
        summary="Update Category",
        description="Update a user's custom category (cannot update system categories)"
    ),
    partial_update=extend_schema(
        summary="Partially Update Category",
        description="Partially update a user's custom category"
    ),
    destroy=extend_schema(
        summary="Delete Category",
        description="Soft delete a user's custom category (cannot delete system categories)"
    ),
)
class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing categories.

    Provides CRUD operations for user categories and read-only access
    to system categories. Uses different serializers based on action.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['type', 'is_active']
    search_fields = ['name']
    ordering_fields = ['name', 'type', 'created_at']
    ordering = ['type', 'name']

    def get_queryset(self):
        """
        Return system categories + user's custom categories.
        System categories have user=NULL.
        """
        user = self.request.user
        return Category.active.filter(
            models.Q(user=user) | models.Q(user__isnull=True)
        ).distinct()

    def get_serializer_class(self):
        """
        Use different serializers based on action:
        - list: Lightweight serializer
        - retrieve: Detailed serializer with extra data
        - create/update: Full serializer with validation
        """
        if self.action == 'list':
            return CategoryListSerializer
        elif self.action == 'retrieve':
            return CategoryDetailSerializer
        return CategorySerializer

    def perform_create(self, serializer):
        """
        Auto-assign user on creation.
        User field is set in serializer.create() method.
        """
        serializer.save()

    def perform_update(self, serializer):
        """
        Validate permissions before updating.
        Users cannot modify system categories or other users' categories.
        """
        category = self.get_object()

        # Check if system category
        if category.is_system_category:
            raise ValidationError({
                'detail': 'System categories cannot be modified.'
            })

        # Check ownership
        if category.user != self.request.user:
            raise PermissionDenied(
                'You can only modify your own categories.'
            )

        serializer.save()

    def perform_destroy(self, instance):
        """
        Soft delete the category.
        Validates that user can only delete their own categories.
        """
        # Check if system category
        if instance.is_system_category:
            raise ValidationError({
                'detail': 'System categories cannot be deleted.'
            })

        # Check ownership
        if instance.user != self.request.user:
            raise PermissionDenied(
                'You can only delete your own categories.'
            )

        # Soft delete
        instance.soft_delete()

    @extend_schema(
        summary="Restore Deleted Category",
        description="Restore a soft-deleted category. Only works for user's own categories.",
        request=None,
        responses={
            200: CategorySerializer,
            400: {'description': 'Category is already active or is a system category'},
            403: {'description': 'Cannot restore other users\' categories'}
        }
    )
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """
        Restore a soft-deleted category.
        Changes is_active from False to True.
        """
        # Get category (even if inactive)
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response(
                {'detail': 'Category not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if system category
        if category.is_system_category:
            return Response(
                {'detail': 'System categories cannot be restored.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check ownership
        if category.user != request.user:
            return Response(
                {'detail': 'You can only restore your own categories.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if already active
        if category.is_active:
            return Response(
                {'detail': 'Category is already active.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Restore
        category.restore()
        serializer = self.get_serializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Get Income Categories",
        description="Get all active income categories (system + user's custom)",
        responses={200: CategoryListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def income(self, request):
        """Get only income categories"""
        categories = self.get_queryset().filter(type='income')
        serializer = CategoryListSerializer(categories, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get Expense Categories",
        description="Get all active expense categories (system + user's custom)",
        responses={200: CategoryListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def expense(self, request):
        """Get only expense categories"""
        categories = self.get_queryset().filter(type='expense')
        serializer = CategoryListSerializer(categories, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get User's Custom Categories",
        description="Get only the categories created by the current user (excludes system categories)",
        responses={200: CategoryListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def my_categories(self, request):
        """Get only user's custom categories (no system categories)"""
        categories = Category.active.filter(user=request.user)
        serializer = CategoryListSerializer(categories, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get System Categories",
        description="Get all system default categories",
        responses={200: CategoryListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def system_categories(self, request):
        categories = Category.active.filter(user__isnull=True)
        serializer = CategoryListSerializer(categories, many=True)
        return Response(serializer.data
                        )