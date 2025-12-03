from rest_framework import serializers
from yaml.serializer import SerializerError

from .models import Account

class AccountSerializer(serializers.ModelSerializer):
    transaction_count = serializers.SerializerMethodField()
    balance_display = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            'id', 'name', 'account_type', 'balance', 'balance_display',
            'currency', 'description', 'transaction_count',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'balance', 'created_at', 'updated_at', 'is_active']

    def validate_name(self, value):
        """
        Ensure account name is unique for user
        """
        user = self.context['request'].user
        value = value.strip()

        query = Account.objects.filter(user=user, name__iexact=value)

        if self.instance:
            query = query.exclude(id=self.instance.id)

        if query.exists():
            raise serializers.ValidationError(
                f"You already have an account named '{value}'."
            )

        return value

    def validate_account_type(self, value):
        """Validate account type"""
        valid_types = ['cash', 'bank', 'credit_card', 'investment', 'other']
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Account type must be one of: {', '.join(valid_types)}"
            )
        return value

    def validate_currency(self, value):
        """Validate currency code (basic validation)"""
        if value and len(value) != 3:
            raise serializers.ValidationError(
                "Currency code must be 3 characters (e.g., USD, EUR, XAF)"
            )
        return value.upper()

    def create(self, validated_data):
        """Auto-assign user on creation"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def get_transaction_count(self, obj):
        """Get count of transactions for this account"""
        return obj.transactions.filter(is_active=True).count()

    def get_balance_display(self, obj):
        """Format balance with currency symbol"""
        currency_symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'XAF': 'FCFA',
            'NGN': '₦',
        }
        symbol = currency_symbols.get(obj.currency, obj.currency)
        return f"{symbol}{obj.balance:,.2f}"

class AccountListSerializer(serializers.ModelSerializer):
    balance_display = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = ['id', 'name', 'account_type', 'balance', 'balance_display', 'currency']

    def get_balance_display(self, obj):
        """Format balance with currency symbol"""
        currency_symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'XAF': 'FCFA',
            'NGN': '₦',
        }
        symbol = currency_symbols.get(obj.currency, obj.currency)
        return f"{symbol}{obj.balance:,.2f}"

class AccountDetailSerializer(serializers.ModelSerializer):
    transaction_count = serializers.SerializerMethodField()
    balance_display = serializers.SerializerMethodField()
    recent_transactions = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            'id', 'name', 'account_type', 'balance', 'balance_display',
            'currency', 'description', 'transaction_count', 'recent_transactions',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'balance', 'created_at', 'updated_at', 'is_active']

    def get_transaction_count(self, obj):
        """Get count of transactions for this account"""
        return obj.transactions.filter(is_active=True).count()

    def get_balance_display(self, obj):
        """Format balance with currency symbol"""
        currency_symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'XAF': 'FCFA',
            'NGN': '₦',
        }
        symbol = currency_symbols.get(obj.currency, obj.currency)
        return f"{symbol}{obj.balance:,.2f}"

    def get_recent_transactions(self, obj):
        """Get last 5 transactions for this account"""
        from apps.transactions.models import Transaction

        transactions = obj.transactions.filter(
            is_active=True
        ).select_related('category').order_by('-transaction_date', '-created_at')[:5]

        return [
            {
                'id': t.id,
                'type': t.type,
                'amount': float(t.amount),
                'description': t.description,
                'category': t.category.name,
                'transaction_date': t.transaction_date,
            }
            for t in transactions
        ]
