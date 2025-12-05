from django.db import models
from django.db.models import Sum, Count, Avg, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from datetime import datetime, date

from .models import Transaction, Tag
from .serializers import (
    TransactionSerializer,
    TransactionListSerializer,
    TransactionDetailSerializer,
    TransactionStatsSerializer,
    TagSerializer
)


@extend_schema_view(
    list=extend_schema(
        summary="List Transactions",
        description="Get all user's transactions with filtering and search",
        parameters=[
            OpenApiParameter(name='type', description='Filter by type (income/expense)', required=False, type=str),
            OpenApiParameter(name='category', description='Filter by category ID', required=False, type=int),
            OpenApiParameter(name='account', description='Filter by account ID', required=False, type=int),
            OpenApiParameter(name='date_from', description='Filter from date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='date_to', description='Filter to date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='amount_min', description='Minimum amount', required=False, type=float),
            OpenApiParameter(name='amount_max', description='Maximum amount', required=False, type=float),
            OpenApiParameter(name='search', description='Search in description and notes', required=False, type=str),
        ]
    ),
    retrieve=extend_schema(
        summary="Get Transaction Details",
        description="Retrieve detailed transaction information with tags and receipts"
    ),
    create=extend_schema(
        summary="Create Transaction",
        description="Create a new transaction. Account balance is automatically updated."
    ),
    update=extend_schema(
        summary="Update Transaction",
        description="Update transaction. Account balance is automatically adjusted."
    ),
    partial_update=extend_schema(
        summary="Partially Update Transaction",
        description="Partially update transaction"
    ),
    destroy=extend_schema(
        summary="Delete Transaction",
        description="Soft delete transaction. Account balance is automatically adjusted."
    ),
)
class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing transactions.

    Automatically updates account balances on create/update/delete.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['type', 'category', 'account', 'is_active']
    search_fields = ['description', 'notes']
    ordering_fields = ['transaction_date', 'amount', 'created_at']
    ordering = ['-transaction_date', '-created_at']

    def get_queryset(self):
        """Return only user's transactions with filters"""
        queryset = Transaction.active.filter(user=self.request.user).select_related(
            'category', 'account'
        ).prefetch_related('tags')

        # Date range filter
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(transaction_date__gte=date_from)
            except ValueError:
                pass

        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(transaction_date__lte=date_to)
            except ValueError:
                pass

        # Amount range filter
        amount_min = self.request.query_params.get('amount_min')
        amount_max = self.request.query_params.get('amount_max')

        if amount_min:
            try:
                queryset = queryset.filter(amount__gte=float(amount_min))
            except ValueError:
                pass

        if amount_max:
            try:
                queryset = queryset.filter(amount__lte=float(amount_max))
            except ValueError:
                pass

        return queryset

    def get_serializer_class(self):
        """Use different serializers based on action"""
        if self.action == 'list':
            return TransactionListSerializer
        elif self.action == 'retrieve':
            return TransactionDetailSerializer
        return TransactionSerializer

    def perform_create(self, serializer):
        """Auto-assign user on creation"""
        serializer.save()

    def perform_update(self, serializer):
        """Validate ownership before updating"""
        transaction = self.get_object()

        if transaction.user != self.request.user:
            raise PermissionDenied('You can only modify your own transactions.')

        serializer.save()

    def perform_destroy(self, instance):
        """Soft delete transaction"""
        if instance.user != self.request.user:
            raise PermissionDenied('You can only delete your own transactions.')

        instance.soft_delete()

    @extend_schema(
        summary="Restore Deleted Transaction",
        description="Restore a soft-deleted transaction",
        request=None,
        responses={200: TransactionSerializer}
    )
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted transaction"""
        try:
            transaction = Transaction.objects.get(pk=pk)
        except Transaction.DoesNotExist:
            return Response(
                {'detail': 'Transaction not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if transaction.user != request.user:
            return Response(
                {'detail': 'You can only restore your own transactions.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if transaction.is_active:
            return Response(
                {'detail': 'Transaction is already active.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        transaction.restore()
        serializer = self.get_serializer(transaction)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Get Transaction Statistics",
        description="Get income/expense statistics for transactions",
        parameters=[
            OpenApiParameter(name='date_from', description='Filter from date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='date_to', description='Filter to date (YYYY-MM-DD)', required=False, type=str),
        ],
        responses={200: TransactionStatsSerializer}
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get transaction statistics"""
        queryset = self.get_queryset()

        income_total = queryset.filter(type='income').aggregate(
            total=Sum('amount')
        )['total'] or 0

        expense_total = queryset.filter(type='expense').aggregate(
            total=Sum('amount')
        )['total'] or 0

        transaction_count = queryset.count()
        income_count = queryset.filter(type='income').count()
        expense_count = queryset.filter(type='expense').count()

        average = queryset.aggregate(avg=Avg('amount'))['avg'] or 0

        stats_data = {
            'total_income': income_total,
            'total_expense': expense_total,
            'net_amount': income_total - expense_total,
            'transaction_count': transaction_count,
            'income_count': income_count,
            'expense_count': expense_count,
            'average_transaction': average,
        }

        serializer = TransactionStatsSerializer(stats_data)
        return Response(serializer.data)

    @extend_schema(
        summary="Get Income Transactions",
        description="Get all income transactions",
        responses={200: TransactionListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def income(self, request):
        """Get only income transactions"""
        transactions = self.get_queryset().filter(type='income')
        serializer = TransactionListSerializer(transactions, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get Expense Transactions",
        description="Get all expense transactions",
        responses={200: TransactionListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def expense(self, request):
        """Get only expense transactions"""
        transactions = self.get_queryset().filter(type='expense')
        serializer = TransactionListSerializer(transactions, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="List Tags",
        description="Get all user's tags with transaction count"
    ),
    retrieve=extend_schema(
        summary="Get Tag Details",
        description="Retrieve tag with transaction count"
    ),
    create=extend_schema(
        summary="Create Tag",
        description="Create a new tag for organizing transactions"
    ),
    update=extend_schema(
        summary="Update Tag",
        description="Update tag name"
    ),
    destroy=extend_schema(
        summary="Delete Tag",
        description="Soft delete tag. Removes tag from all transactions."
    ),
)
class TagViewSet(viewsets.ModelViewSet):
    """ViewSet for managing transaction tags"""
    permission_classes = [IsAuthenticated]
    serializer_class = TagSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering = ['name']

    def get_queryset(self):
        """Return only user's tags"""
        return Tag.active.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Auto-assign user on tag creation"""
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        """Validate ownership before updating"""
        tag = self.get_object()

        if tag.user != self.request.user:
            raise PermissionDenied('You can only modify your own tags.')

        serializer.save()

    def perform_destroy(self, instance):
        """Soft delete tag"""
        if instance.user != self.request.user:
            raise PermissionDenied('You can only delete your own tags.')

        instance.soft_delete()

    @extend_schema(
        summary="Restore Deleted Tag",
        description="Restore a soft-deleted tag",
        request=None,
        responses={200: TagSerializer}
    )
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted tag"""
        try:
            tag = Tag.objects.get(pk=pk)
        except Tag.DoesNotExist:
            return Response(
                {'detail': 'Tag not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if tag.user != request.user:
            return Response(
                {'detail': 'You can only restore your own tags.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if tag.is_active:
            return Response(
                {'detail': 'Tag is already active.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        tag.restore()
        serializer = self.get_serializer(tag)
        return Response(serializer.data, status=status.HTTP_200_OK)
