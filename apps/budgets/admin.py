from django.contrib import admin
from .models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'amount', 'period_type', 'start_date', 'end_date', 'is_active']
    list_filter = ['period_type', 'is_active', 'start_date']
    search_fields = ['user__email', 'category__name']
    list_per_page = 25
    date_hierarchy = 'start_date'
