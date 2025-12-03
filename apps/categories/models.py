from django.db import models
from django.conf import settings
from apps.core.models import BaseModel
from apps.core.managers import ActiveManager

class Category(BaseModel):
    TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='categories',
        null=True,
        blank=True,
       help_text='NULL means system default category'
    )
    name = models.CharField(max_length=120)
    type = models.CharField(max_length=7, choices=TYPE_CHOICES)
    icon = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        help_text='Hex color code (e.g., #FF5733)'
    )

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        db_table = 'categories'
        ordering = ['user', 'name', 'type']
        models.UniqueConstraint(
            fields = ['name', 'type'],
            condition = models.Q(user__isnull=True),
            name = 'unique_system_category'
        ),
        indexes = [
            models.Index(fields=['user', 'type']),
            models.Index(fields=['type', 'is_active']),
        ]

        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        if self.user:
            return f"{self.user.email} - {self.name} ({self.type})"
        return f"System - {self.name} ({self.type})"

    @property
    def is_system_category(self):
        return self.user is None

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.color and not self.color.startswith('#'):
            raise ValidationError({
                'color': 'Color must be a valid hex color code'
            })
        if self.color and len(self.color) != 7:
            raise ValidationError({'color': 'Color must be 7 characters (e.g., #FF5733)'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)