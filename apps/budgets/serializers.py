from rest_framework import serializers
from django.utils import timezone
from datetime import date
from decimal import Decimal
from .models import Budget


class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    spent_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    percentage_used = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            'id', 'category', 'category_name', 'amount', 'period_type',
            'start_date', 'end_date', 'spent_amount', 'remaining_amount',
            'percentage_used', 'status', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_active']

    def validate_amount(self, value):
        """Ensure amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Budget amount must be greater than zero.")
        return value

    # def validate_start_date(self, value):
    #     """Validate start date"""
    #     # Can't start too far in the past (optional business rule)
    #     # This is just an example - adjust as needed
    #     return value

    def validate(self, attrs):
        """Object-level validation"""
        user = self.context['request'].user

        # Validate category belongs to user or is system category
        category = attrs.get('category')
        if category:
            if category.user and category.user != user:
                raise serializers.ValidationError({
                    'category': 'You can only use your own categories or system categories.'
                })

            # Validate category is expense type
            if category.type != 'expense':
                raise serializers.ValidationError({
                    'category': 'Budgets can only be created for expense categories.'
                })

        # Validate end_date is after start_date
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')

        if end_date and start_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': 'End date must be after start date.'
            })

        # Check for duplicate budget (same category, period, start date)
        if not self.instance:  # Only for creation
            existing = Budget.objects.filter(
                user=user,
                category=category,
                period_type=attrs.get('period_type'),
                start_date=start_date,
                is_active=True
            )

            if existing.exists():
                raise serializers.ValidationError(
                    'A budget already exists for this category and period.'
                )

        return attrs

    def create(self, validated_data):
        """Auto-assign user on creation"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def get_spent_amount(self, obj):
        """Get amount spent in budget period"""
        return float(obj.get_spent_amount())

    def get_remaining_amount(self, obj):
        """Get remaining budget amount"""
        return float(obj.get_remaining_amount())

    def get_percentage_used(self, obj):
        """Get percentage of budget used"""
        return round(float(obj.get_percentage_used()), 2)

    def get_status(self, obj):
        """Get budget status"""
        percentage = obj.get_percentage_used()

        if percentage >= 100:
            return 'exceeded'
        elif percentage >= 80:
            return 'warning'
        elif percentage >= 50:
            return 'on_track'
        else:
            return 'good'


class BudgetListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    spent_amount = serializers.SerializerMethodField()
    percentage_used = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            'id', 'category_name', 'amount', 'period_type',
            'start_date', 'end_date', 'spent_amount',
            'percentage_used', 'status'
        ]

    def get_spent_amount(self, obj):
        return float(obj.get_spent_amount())

    def get_percentage_used(self, obj):
        return round(float(obj.get_percentage_used()), 2)

    def get_status(self, obj):
        percentage = obj.get_percentage_used()
        if percentage >= 100:
            return 'exceeded'
        elif percentage >= 80:
            return 'warning'
        elif percentage >= 50:
            return 'on_track'
        else:
            return 'good'


class BudgetDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_type = serializers.CharField(source='category.type', read_only=True)
    spent_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    percentage_used = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    recent_transactions = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            'id', 'category', 'category_name', 'category_type',
            'amount', 'period_type', 'start_date', 'end_date',
            'spent_amount', 'remaining_amount', 'percentage_used',
            'status', 'days_remaining', 'recent_transactions',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_active']

    def get_spent_amount(self, obj):
        return float(obj.get_spent_amount())

    def get_remaining_amount(self, obj):
        return float(obj.get_remaining_amount())

    def get_percentage_used(self, obj):
        return round(float(obj.get_percentage_used()), 2)

    def get_status(self, obj):
        percentage = obj.get_percentage_used()
        if percentage >= 100:
            return 'exceeded'
        elif percentage >= 80:
            return 'warning'
        elif percentage >= 50:
            return 'on_track'
        else:
            return 'good'

    def get_days_remaining(self, obj):
        """Calculate days remaining in budget period"""
        if not obj.end_date:
            return None

        today = date.today()
        if today > obj.end_date:
            return 0

        return (obj.end_date - today).days

    def get_recent_transactions(self, obj):
        """Get recent transactions for this budget"""
        from apps.transactions.models import Transaction

        query_filters = {
            'user': obj.user,
            'category': obj.category,
            'type': 'expense',
            'transaction_date__gte': obj.start_date,
            'is_active': True
        }

        if obj.end_date:
            query_filters['transaction_date__lte'] = obj.end_date

        transactions = Transaction.objects.filter(**query_filters).order_by(
            '-transaction_date', '-created_at'
        )[:5]

        return [
            {
                'id': t.id,
                'amount': float(t.amount),
                'description': t.description,
                'transaction_date': t.transaction_date,
            }
            for t in transactions
        ]


class BudgetSummarySerializer(serializers.Serializer):
    """Serializer for budget summary statistics"""
    total_budgets = serializers.IntegerField()
    total_budget_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_spent = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_remaining = serializers.DecimalField(max_digits=15, decimal_places=2)
    budgets_exceeded = serializers.IntegerField()
    budgets_warning = serializers.IntegerField()
    budgets_on_track = serializers.IntegerField()
    budgets_good = serializers.IntegerField()
    average_usage_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
