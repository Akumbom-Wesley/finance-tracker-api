from django.contrib import admin
from .models import Transaction, Tag, TransactionTag, Receipt


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'type', 'amount', 'category', 'transaction_date', 'is_active']
    list_filter = ['type', 'transaction_date', 'is_active', 'category']
    search_fields = ['description', 'notes', 'user__email']
    list_per_page = 50
    date_hierarchy = 'transaction_date'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'user__email']


@admin.register(TransactionTag)
class TransactionTagAdmin(admin.ModelAdmin):
    list_display = ['transaction', 'tag', 'created_at']
    list_filter = ['created_at']
    search_fields = ['transaction__description', 'tag__name']


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['id', 'transaction', 'file_name', 'file_size', 'created_at']
    list_filter = ['created_at', 'mime_type']
    search_fields = ['file_name', 'transaction__description']
