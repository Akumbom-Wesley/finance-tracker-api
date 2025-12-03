from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from apps.core.models import BaseModel
from apps.core.managers import ActiveManager


class Transaction(BaseModel):
    TRANSACTION_TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    account = models.ForeignKey(
        'accounts.Account',
        on_delete=models.SET_NULL,
        related_name='transactions',
        null=True,
        blank=True
    )
    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.PROTECT,
        related_name='transactions'
    )
    type = models.CharField(max_length=7, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    description = models.CharField(max_length=255)
    notes = models.TextField(blank=True, null=True)
    transaction_date = models.DateField()

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        db_table = 'transactions'
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'transaction_date']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'type']),
            models.Index(fields=['transaction_date', 'is_active']),
        ]

    def __str__(self):
        return f"{self.type}: {self.amount} - {self.description}"

    def clean(self):
        if self.amount <= 0:
            raise ValidationError({'amount': 'Amount must be greater than zero.'})

        if self.category and self.category.type != self.type:
            raise ValidationError({
                'category': f'Category type ({self.category.type}) must match transaction type ({self.type}).'
            })

        if self.account and self.account.user != self.user:
            raise ValidationError({
                'account': 'Account must belong to the transaction user.'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        is_new = self.pk is None

        if not is_new:
            old_transaction = Transaction.objects.get(pk=self.pk)
            if old_transaction.account:
                if old_transaction.type == 'income':
                    old_transaction.account.update_balance(-old_transaction.amount)
                else:
                    old_transaction.account.update_balance(old_transaction.amount)

        super().save(*args, **kwargs)

        if self.account:
            if self.type == 'income':
                self.account.update_balance(self.amount)
            else:
                self.account.update_balance(-self.amount)


class Tag(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tags'
    )
    name = models.CharField(max_length=50)

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        db_table = 'tags'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_user_tag'
            ),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.name}"


class TransactionTag(models.Model):
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='transaction_tags'
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name='transaction_tags'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transaction_tags'
        constraints = [
            models.UniqueConstraint(
                fields=['transaction', 'tag'],
                name='unique_transaction_tag'
            ),
        ]
        indexes = [
            models.Index(fields=['transaction']),
            models.Index(fields=['tag']),
        ]

    def __str__(self):
        return f"{self.transaction.id} - {self.tag.name}"


class Receipt(BaseModel):
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='receipts'
    )
    file_path = models.FileField(upload_to='receipts/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text='File size in bytes')
    mime_type = models.CharField(max_length=100)

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        db_table = 'receipts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction', 'is_active']),
        ]

    def __str__(self):
        return f"Receipt for Transaction {self.transaction.id}"
