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
    name = models.CharField(max_length=100)
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
        ordering = ['type', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name', 'type'],
                name='unique_user_category'
            ),
            models.UniqueConstraint(
                fields=['name', 'type'],
                condition=models.Q(user__isnull=True),
                name='unique_system_category'
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'type']),
            models.Index(fields=['type', 'is_active']),
        ]

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
            raise ValidationError({'color': 'Color must be a valid hex code starting with #'})

        if self.color and len(self.color) != 7:
            raise ValidationError({'color': 'Color must be 7 characters (e.g., #FF5733)'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_transaction_count(self):
        """Get count of active transactions using this category"""
        return self.transactions.filter(is_active=True).count()
