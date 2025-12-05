from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import Transaction

@receiver(pre_save, sender=Transaction)
def handle_transaction_update(sender, instance, **kwargs):
    """
      Handle balance updates when transaction is modified.
      Reverts old balance change before new one is applied in model.save()
    """

    if instance.pk:
        try:
            old_transaction = Transaction.objects.get(pk=instance.pk)

            #Revert old transaction's balance effect
            if old_transaction.amount:
                if old_transaction.type == 'income':
                    old_transaction.account.update_balance(-old_transaction.amount)
                else:
                    old_transaction.account.update_balance(old_transaction.amount)
        except Transaction.DoesNotExist:
            pass

@receiver(post_delete, sender=Transaction)
def handle_transaction_delete(sender, instance, **kwargs):
    """
     Revert balance when transaction is hard deleted.
     Note: We use soft delete, but this handles edge cases.
     """
    if instance.account:
        if instance.type == 'income':
            instance.account.update_balance(-instance.amount)
        else:
            instance.account.update_balance(instance.amount)
