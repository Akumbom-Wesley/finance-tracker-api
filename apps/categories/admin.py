from django.contrib import admin
from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'user', 'icon', 'color', 'is_active', 'created_at']
    list_filter = ['type', 'is_active', 'created_at']
    search_fields = ['name', 'user__email']
    list_per_page = 10

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'type')
        }),
        ('Styling', {
            'fields': ('icon', 'color')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request)
