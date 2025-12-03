from rest_framework import serializers
from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    is_system_category = serializers.ReadOnlyField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'type', 'icon', 'color',
            'is_system_category', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_active']

    def validate_name(self, value):
        """Ensure category name is unique for user and type"""
        user = self.context['request'].user
        category_type = self.initial_data.get('type')

        # Normalize name (strip whitespace, title case)
        value = value.strip()

        # Build query to check for duplicates
        query = Category.objects.filter(
            user=user,
            name__iexact=value,  # Case-insensitive check
            type=category_type
        )

        # Exclude current instance if updating
        if self.instance:
            query = query.exclude(id=self.instance.id)

        if query.exists():
            raise serializers.ValidationError(
                f"You already have a {category_type} category named '{value}'."
            )

        return value

    def validate_color(self, value):
        """Validate hex color format"""
        if not value:  # Allow empty/null colors
            return value

        value = value.strip()

        if not value.startswith('#'):
            raise serializers.ValidationError(
                "Color must start with # (e.g., #FF5733)"
            )

        if len(value) != 7:
            raise serializers.ValidationError(
                "Color must be 7 characters including # (e.g., #FF5733)"
            )

        # Validate hex characters
        try:
            int(value[1:], 16)  # Try to parse as hex
        except ValueError:
            raise serializers.ValidationError(
                "Color must contain valid hex characters (0-9, A-F)"
            )

        return value.upper()  # Normalize to uppercase

    def validate_type(self, value):
        """Validate category type (simpler than in validate())"""
        if value not in ['income', 'expense']:
            raise serializers.ValidationError(
                "Type must be either 'income' or 'expense'."
            )
        return value

    def validate(self, attrs):
        """
        Object-level validation.
        Runs after all field-level validations.
        """
        # Additional cross-field validation can go here if needed
        return attrs

    def create(self, validated_data):
        """Auto-assign user on creation"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class CategoryListSerializer(serializers.ModelSerializer):
    is_system_category = serializers.ReadOnlyField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'type', 'icon', 'color', 'is_system_category']


class CategoryDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer with related data.
    Use for single category retrieval.
    """
    is_system_category = serializers.ReadOnlyField()
    transaction_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'type', 'icon', 'color',
            'is_system_category', 'is_active',
            'transaction_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_active']

    def get_transaction_count(self, obj):
        """Get count of transactions using this category"""
        return obj.transaction_set.filter(is_active=True).count()