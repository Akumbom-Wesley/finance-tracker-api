from django.db import models
from django.db.models import Sum, Count, Q, F
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from datetime import date, timedelta
from decimal import Decimal

from .models import Budget
from .serializers import (
    BudgetSerializer,
    BudgetListSerializer,
    BudgetDetailSerializer,
    BudgetSummarySerializer
)


@extend_schema_view(
    list=extend_schema(
        summary="List Budgets",
        description="Get all user's budgets with spending calculations",
        parameters=[
            OpenApiParameter(name='period_type', description='Filter by period type (monthly/yearly)', required=False, type=str),
            OpenApiParameter(name='category', description='Filter by category ID', required=False, type=int),
            OpenApiParameter(name='status', description='Filter by status (exceeded/warning/on_track/good)', required=False, type=str),
        ]
    ),
    retrieve=extend_schema(
        summary="Get Budget Details",
        description="Retrieve detailed budget information with transactions"
    ),
    create=extend_schema(
        summary="Create Budget",
        description="Create a new budget for an expense category"
    ),
    update=extend_schema(
        summary="Update Budget",
        description="Update budget amount or period"
    ),
    partial_update=extend_schema(
        summary="Partially Update Budget",
        description="Partially update budget"
    ),
    destroy=extend_schema(
        summary="Delete Budget",
        description="Soft delete budget"
    ),
)

class BudgetViewSet(viewsets.ModelViewSet):
    """
      ViewSet for managing budgets.

      Automatically calculates spending and tracks budget progress.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['period_type', 'category', 'is_active']
    search_fields = ['category__name']
    ordering_fields = ['start_date', 'amount', 'created_at']
    ordering = ['-start_date']

    def get_queryset(self):
        """Return only the user's budget with optional status filter"""
        queryset = Budget.active.filter(user=self.request.user).select_related('category')

        #Status filter
        status_filter = self.request.query_params.get('status')
        if status_filter:
            budget_ids = []
            for budget in queryset:
                percentage = budget.get_percentage_used()

                if status_filter == 'exceeded' and percentage >= 100:
                    budget_ids.append(budget.id)
                elif status_filter == 'warning' and 80 <= percentage < 100:
                    budget_ids.append(budget.id)
                elif status_filter == 'on_track' and 50 <= percentage < 80:
                    budget_ids.append(budget.id)
                elif status_filter == 'good' and percentage < 50:
                    budget_ids.append(budget.id)

            queryset = queryset.filter(id__in=budget_ids)

        return queryset

    def get_serializer_class(self):
        """Use different serializer class based on action"""
        if self.action == "list":
            return BudgetListSerializer
        elif self.action == "retrieve":
            return BudgetDetailSerializer
        return BudgetSerializer

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        """Validate ownership before updating"""
        budget = self.get_object()

        if budget.user != self.request.user:
            raise PermissionDenied('You can only modify your own budgets.')

        serializer.save()

    def perform_destroy(self, instance):
        """Soft delete budget"""
        if instance.user != self.request.user:
            raise PermissionDenied('You can only delete your own budgets.')

        instance.soft_delete()

    @extend_schema(
        summary="Restore Deleted Budget",
        description="Restore a soft-deleted budget",
        request=None,
        responses={200: BudgetSerializer}
    )
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted budget"""
        try:
            budget = Budget.objects.get(pk=pk)
        except Budget.DoesNotExist:
            return Response(
                {'detail': 'Budget not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if budget.user != request.user:
            return Response(
                {'detail': 'You can only restore your own budgets.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if budget.is_active:
            return Response(
                {'detail': 'Budget is already active.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        budget.restore()
        serializer = self.get_serializer(budget)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Get Budget Summary",
        description="Get summary statistics for all budgets",
        responses={200: BudgetSummarySerializer}
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get Budget Summary Statistics"""
        budgets = self.get_queryset()

        total_budgets = budgets.count()
        total_budget_amount = budgets.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Calculate spending and categorize
        total_spent = Decimal('0')
        exceeded = 0
        warning = 0
        on_track = 0
        good = 0
        total_percentage = Decimal('0')

        for budget in budgets:
            spent = budget.get_spent_amount()
            total_spent += spent

            percentage = budget.get_percentage_used()
            total_percentage += percentage

            if percentage >= 100:
                exceeded += 1
            elif percentage >= 80:
                warning += 1
            elif percentage >= 50:
                on_track += 1
            else:
                good += 1

        average_usage = (total_percentage / total_budgets) if total_budgets > 0 else Decimal('0')

        summary_data = {
            'total_budgets': total_budgets,
            'total_budget_amount': total_budget_amount,
            'total_spent': total_spent,
            'total_remaining': total_budget_amount - total_spent,
            'budgets_exceeded': exceeded,
            'budgets_warning': warning,
            'budgets_on_track': on_track,
            'budgets_good': good,
            'average_usage_percentage': average_usage,
        }

        serializer = BudgetSummarySerializer(summary_data)
        return Response(serializer.data)

    @extend_schema(
        summary="Get Exceeded Budgets",
        description="Get all budgets that have been exceeded",
        responses={200: BudgetListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def exceeded(self, request):
        """Get budgets that have been exceeded"""
        budgets = self.get_queryset()
        exceeded_budgets = [b for b in budgets if b.is_exceeded]
        serializer = BudgetListSerializer(exceeded_budgets, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get Active Monthly Budgets",
        description="Get all active monthly budgets for current month",
        responses={200: BudgetListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def current_month(self, request):
        """Get budgets for current month"""
        today = date.today()
        budgets = self.get_queryset().filter(
            period_type='monthly',
            start_date__year=today.year,
            start_date__month=today.month
        )
        serializer = BudgetListSerializer(budgets, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get Category Spending Analysis",
        description="Analyze spending by category with budget comparison",
        responses={200: {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'category_name': {'type': 'string'},
                    'budget_amount': {'type': 'number'},
                    'spent_amount': {'type': 'number'},
                    'remaining': {'type': 'number'},
                    'percentage_used': {'type': 'number'},
                    'status': {'type': 'string'}
                }
            }
        }}
    )
    @action(detail=False, methods=['get'])
    def category_analysis(self, request):
        """Get spending analysis by category"""
        budgets = self.get_queryset()

        analysis = []
        for budget in budgets:
            spent = budget.get_spent_amount()
            remaining = budget.get_remaining_amount()
            percentage = budget.get_percentage_used()

            if percentage >= 100:
                status_val = 'exceeded'
            elif percentage >= 80:
                status_val = 'warning'
            elif percentage >= 50:
                status_val = 'on_track'
            else:
                status_val = 'good'

            analysis.append({
                'category_id': budget.category.id,
                'category_name': budget.category.name,
                'budget_amount': float(budget.amount),
                'spent_amount': float(spent),
                'remaining': float(remaining),
                'percentage_used': round(float(percentage), 2),
                'status': status_val,
                'period_type': budget.period_type,
                'start_date': budget.start_date,
                'end_date': budget.end_date,
            })

        # Sort by percentage used (highest first)
        analysis.sort(key=lambda x: x['percentage_used'], reverse=True)

        return Response(analysis)