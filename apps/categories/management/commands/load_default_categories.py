from django.core.management.base import BaseCommand
from ...models import Category

class Command(BaseCommand):
    help = 'Loads default system categories for income and expense'

    def handle(self, *args, **kwargs):
        default_categories = [
            # Income categories
            {'name': 'Salary', 'type': 'income', 'icon': 'briefcase', 'color': '#4CAF50'},
            {'name': 'Freelance', 'type': 'income', 'icon': 'laptop', 'color': '#8BC34A'},
            {'name': 'Investment', 'type': 'income', 'icon': 'trending-up', 'color': '#009688'},
            {'name': 'Gift', 'type': 'income', 'icon': 'gift', 'color': '#00BCD4'},
            {'name': 'Business', 'type': 'income', 'icon': 'briefcase', 'color': '#03A9F4'},
            {'name': 'Other Income', 'type': 'income', 'icon': 'plus-circle', 'color': '#2196F3'},

            # Expense categories
            {'name': 'Food & Dining', 'type': 'expense', 'icon': 'coffee', 'color': '#F44336'},
            {'name': 'Transportation', 'type': 'expense', 'icon': 'car', 'color': '#E91E63'},
            {'name': 'Housing', 'type': 'expense', 'icon': 'home', 'color': '#9C27B0'},
            {'name': 'Utilities', 'type': 'expense', 'icon': 'zap', 'color': '#673AB7'},
            {'name': 'Healthcare', 'type': 'expense', 'icon': 'heart', 'color': '#3F51B5'},
            {'name': 'Entertainment', 'type': 'expense', 'icon': 'film', 'color': '#FF5722'},
            {'name': 'Shopping', 'type': 'expense', 'icon': 'shopping-bag', 'color': '#FF9800'},
            {'name': 'Education', 'type': 'expense', 'icon': 'book', 'color': '#FFC107'},
            {'name': 'Personal Care', 'type': 'expense', 'icon': 'user', 'color': '#FFEB3B'},
            {'name': 'Insurance', 'type': 'expense', 'icon': 'shield', 'color': '#CDDC39'},
            {'name': 'Debt Payment', 'type': 'expense', 'icon': 'credit-card', 'color': '#795548'},
            {'name': 'Other Expense', 'type': 'expense', 'icon': 'more-horizontal', 'color': '#607D8B'},
        ]

        created_count = 0
        skipped_count = 0

        for cat_data in default_categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                type=cat_data['type'],
                user=None,  # System category
                defaults={
                    'icon': cat_data['icon'],
                    'color': cat_data['color'],
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created: {category.name} ({category.type})')
                )
            else:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(f'- Skipped: {category.name} (already exists)')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"=" * 60}\n'
                f'Summary: {created_count} created, {skipped_count} skipped\n'
                f'{"=" * 60}'
            )
        )