from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from .models import Account
from .serializers import AccountSerializer, AccountListSerializer, AccountDetailSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List Accounts",
        description="Get all user's accounts with balance information",
        parameters=[
            OpenApiParameter(
                name='account_type',
                description='Filter by account type (cash/bank/credit_card/investment/other)',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='currency',
                description='Filter by currency code (USD/EUR/XAF/etc.)',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='search',
                description='Search in account name and description',
                required=False,
                type=str
            ),
        ]
    ),
    retrieve=extend_schema(
        summary="Get Account Details",
        description="Retrieve detailed account information including recent transactions"
    ),
    create=extend_schema(
        summary="Create Account",
        description="Create a new account. Initial balance is 0. User is automatically assigned."
    ),
    update=extend_schema(
        summary="Update Account",
        description="Update account details (name, type, currency, description). Balance cannot be directly modified."
    ),
    partial_update=extend_schema(
        summary="Partially Update Account",
        description="Partially update account details"
    ),
    destroy=extend_schema(
        summary="Delete Account",
        description="Soft delete an account. Cannot delete if account has transactions."
    ),
)
class AccountViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user accounts.

    Provides CRUD operations for accounts with balance tracking.
    Balance is automatically updated when transactions are created/modified.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['account_type', 'currency', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'balance', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return only user's own accounts"""
        return Account.active.filter(user=self.request.user)

    def get_serializer_class(self):
        """Use different serializers based on action"""
        if self.action == 'list':
            return AccountListSerializer
        elif self.action == 'retrieve':
            return AccountDetailSerializer
        return AccountSerializer

    def perform_create(self, serializer):
        """Auto-assign user on creation"""
        serializer.save()

    def perform_update(self, serializer):
        """Validate ownership before updating"""
        account = self.get_object()

        if account.user != self.request.user:
            raise PermissionDenied('You can only modify your own accounts.')

        serializer.save()

    def perform_destroy(self, instance):
        """
        Soft delete account.
        Prevent deletion if account has transactions.
        """
        if instance.user != self.request.user:
            raise PermissionDenied('You can only delete your own accounts.')

        # Check if account has transactions
        transaction_count = instance.transactions.filter(is_active=True).count()
        if transaction_count > 0:
            raise ValidationError({
                'detail': f'Cannot delete account with {transaction_count} active transaction(s). '
                          'Please delete or reassign transactions first.'
            })

        instance.soft_delete()

    @extend_schema(
        summary="Restore Deleted Account",
        description="Restore a soft-deleted account",
        request=None,
        responses={
            200: AccountSerializer,
            400: {'description': 'Account is already active'},
            403: {'description': 'Cannot restore other users\' accounts'}
        }
    )
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted account"""
        try:
            account = Account.objects.get(pk=pk)
        except Account.DoesNotExist:
            return Response(
                {'detail': 'Account not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if account.user != request.user:
            return Response(
                {'detail': 'You can only restore your own accounts.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if account.is_active:
            return Response(
                {'detail': 'Account is already active.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        account.restore()
        serializer = self.get_serializer(account)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Get Account Summary",
        description="Get total balance across all accounts grouped by currency",
        responses={200: {
            'type': 'object',
            'properties': {
                'total_accounts': {'type': 'integer'},
                'balances_by_currency': {'type': 'object'},
                'accounts_by_type': {'type': 'object'}
            }
        }}
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get account summary statistics"""
        accounts = self.get_queryset()

        # Total accounts
        total_accounts = accounts.count()

        # Balance by currency
        balances = accounts.values('currency').annotate(
            total=models.Sum('balance')
        )
        balances_by_currency = {
            item['currency']: float(item['total'])
            for item in balances
        }

        # Accounts by type
        accounts_by_type = accounts.values('account_type').annotate(
            count=models.Count('id'),
            total_balance=models.Sum('balance')
        )
        accounts_by_type_data = {
            item['account_type']: {
                'count': item['count'],
                'total_balance': float(item['total_balance'])
            }
            for item in accounts_by_type
        }

        return Response({
            'total_accounts': total_accounts,
            'balances_by_currency': balances_by_currency,
            'accounts_by_type': accounts_by_type_data
        })

    @extend_schema(
        summary="Get Accounts by Type",
        description="Get all accounts filtered by specific type",
        parameters=[
            OpenApiParameter(
                name='type',
                description='Account type',
                required=True,
                type=str,
                location=OpenApiParameter.PATH
            )
        ],
        responses={200: AccountListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='by-type/(?P<type>[^/.]+)')
    def by_type(self, request, type=None):
        """Get accounts by specific type"""
        valid_types = ['cash', 'bank', 'credit_card', 'investment', 'other']

        if type not in valid_types:
            return Response(
                {'detail': f'Invalid account type. Must be one of: {", ".join(valid_types)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        accounts = self.get_queryset().filter(account_type=type)
        serializer = AccountListSerializer(accounts, many=True)
        return Response(serializer.data)
