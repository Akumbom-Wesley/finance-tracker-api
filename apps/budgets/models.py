from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from apps.core.models import BaseModel
from apps.core.managers import ActiveManager


class Budget(BaseModel):
    PERIOD_TYPE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='budgets'
    )
    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.PROTECT,
        related_name='budgets'
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        db_table = 'budgets'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'start_date', 'end_date']),
            models.Index(fields=['is_active']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'category', 'period_type', 'start_date'],
                name='unique_budget_per_category_period'
            ),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.category.name} ({self.period_type}): {self.amount}"

    def clean(self):
        if self.amount <= 0:
            raise ValidationError({'amount': 'Budget amount must be greater than zero.'})

        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'End date must be after start date.'})

        if self.category and self.category.type != 'expense':
            raise ValidationError({
                'category': 'Budgets can only be created for expense categories.'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_spent_amount(self):
        """Calculate total spent in this budget period"""
        from apps.transactions.models import Transaction

        query_filters = {
            'user': self.user,
            'category': self.category,
            'type': 'expense',
            'transaction_date__gte': self.start_date,
            'is_active': True
        }

        if self.end_date:
            query_filters['transaction_date__lte'] = self.end_date

        spent = Transaction.objects.filter(**query_filters).aggregate(
            total=models.Sum('amount')
        )['total'] or 0

        return spent

    def get_remaining_amount(self):
        """Calculate remaining budget"""
        return self.amount - self.get_spent_amount()

    def get_percentage_used(self):
        """Calculate percentage of budget used"""
        spent = self.get_spent_amount()
        if self.amount == 0:
            return 0
        return (spent / self.amount) * 100

    @property
    def is_exceeded(self):
        """Check if budget is exceeded"""
        return self.get_spent_amount() > self.amount
