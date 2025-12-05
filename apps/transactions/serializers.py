from rest_framework import serializers
from django.utils import timezone
from datetime import date
from .models import Transaction, Tag


class TagSerializer(serializers.ModelSerializer):
    transaction_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ['id', 'name', 'transaction_count', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at', 'is_active']

    def validate_name(self, value):
        """Ensure tag name is unique for user"""
        user = self.context['request'].user
        value = value.strip().lower()

        query = Tag.objects.filter(user=user, name__iexact=value)

        if self.instance:
            query = query.exclude(id=self.instance.id)

        if query.exists():
            raise serializers.ValidationError(
                f"You already have a tag named '{value}'."
            )

        return value

    def create(self, validated_data):
        """Auto-assign user on creation"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def get_transaction_count(self, obj):
        """Get count of transactions with this tag"""
        return obj.get_transaction_count()


class TransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    tag_names = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id', 'account', 'account_name', 'category', 'category_name',
            'type', 'amount', 'description', 'notes', 'transaction_date',
            'tags', 'tag_names', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_active']

    def validate_amount(self, value):
        """Ensure amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate_transaction_date(self, value):
        """Ensure transaction date is not in the future"""
        if value > date.today():
            raise serializers.ValidationError("Transaction date cannot be in the future.")
        return value

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

            # Validate category type matches transaction type
            transaction_type = attrs.get('type')
            if category.type != transaction_type:
                raise serializers.ValidationError({
                    'category': f'Category type ({category.type}) must match transaction type ({transaction_type}).'
                })

        # Validate account belongs to user
        account = attrs.get('account')
        if account and account.user != user:
            raise serializers.ValidationError({
                'account': 'You can only use your own accounts.'
            })

        # Validate tags belong to user
        tags = attrs.get('tags', [])
        for tag in tags:
            if tag.user != user:
                raise serializers.ValidationError({
                    'tags': f'Tag "{tag.name}" does not belong to you.'
                })

        return attrs

    def create(self, validated_data):
        """Auto-assign user and handle tags"""
        tags = validated_data.pop('tags', [])
        validated_data['user'] = self.context['request'].user

        transaction = super().create(validated_data)

        if tags:
            transaction.tags.set(tags)

        return transaction

    def update(self, instance, validated_data):
        """Handle tags on update"""
        tags = validated_data.pop('tags', None)

        transaction = super().update(instance, validated_data)

        if tags is not None:
            transaction.tags.set(tags)

        return transaction

    def get_tag_names(self, obj):
        """Get list of tag names"""
        return [tag.name for tag in obj.tags.all()]


class TransactionListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'type', 'amount', 'description', 'transaction_date',
            'category_name', 'account_name'
        ]


class TransactionDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_type = serializers.CharField(source='category.type', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    account_balance = serializers.DecimalField(
        source='account.balance',
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    tags = TagSerializer(many=True, read_only=True)
    receipt_count = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id', 'account', 'account_name', 'account_balance',
            'category', 'category_name', 'category_type',
            'type', 'amount', 'description', 'notes', 'transaction_date',
            'tags', 'receipt_count',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_active']

    def get_receipt_count(self, obj):
        """Get count of receipts for this transaction"""
        return obj.receipts.filter(is_active=True).count()


class TransactionStatsSerializer(serializers.Serializer):
    """Serializer for transaction statistics"""
    total_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_expense = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    transaction_count = serializers.IntegerField()
    income_count = serializers.IntegerField()
    expense_count = serializers.IntegerField()
    average_transaction = serializers.DecimalField(max_digits=15, decimal_places=2)
