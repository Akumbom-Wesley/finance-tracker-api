from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from apps.core.models import BaseModel
from apps.core.managers import ActiveManager


class Account(BaseModel):
    ACCOUNT_TYPE_CHOICES = [
        ('cash', 'Cash'),
        ('bank', 'Bank Account'),
        ('credit_card', 'Credit Card'),
        ('investment', 'Investment Account'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='accounts'
    )
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    currency = models.CharField(max_length=3, default='XAF')
    description = models.TextField(blank=True, null=True)

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        db_table = 'accounts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'account_type']),
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.name} ({self.account_type})"

    def update_balance(self, amount):
        """Update account balance (can be positive or negative)"""
        self.balance += amount
        self.save(update_fields=['balance', 'updated_at'])
