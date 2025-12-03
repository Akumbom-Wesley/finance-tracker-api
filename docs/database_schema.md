# Finance Tracker Database Schema

## Entity Relationship Diagram


## Tables

### users (Django built-in + custom fields)
- id (PK)
- email (unique)
- username (unique)
- password
- first_name
- last_name
- is_active
- date_joined

### user_profiles
- id (PK)
- user_id (FK → users, unique)
- currency
- timezone
- avatar
- created_at
- updated_at

### categories
- id (PK)
- user_id (FK → users, nullable for system categories)
- name
- type (income/expense)
- icon
- color
- is_active
- created_at
- updated_at
**Unique:** (user_id, name, type) and (name, type) where user_id IS NULL

### accounts
- id (PK)
- user_id (FK → users)
- name
- account_type (cash/bank/credit_card/investment/other)
- balance
- currency
- description
- is_active
- created_at
- updated_at

### transactions
- id (PK)
- user_id (FK → users)
- account_id (FK → accounts, nullable)
- category_id (FK → categories, PROTECT)
- type (income/expense)
- amount
- description
- notes
- transaction_date
- is_active
- created_at
- updated_at
**Indexes:** (user_id, transaction_date), (user_id, category_id), (user_id, type)

### tags
- id (PK)
- user_id (FK → users)
- name
- is_active
- created_at
- updated_at
**Unique:** (user_id, name)

### transaction_tags (junction table)
- id (PK)
- transaction_id (FK → transactions)
- tag_id (FK → tags)
- created_at
**Unique:** (transaction_id, tag_id)

### receipts
- id (PK)
- transaction_id (FK → transactions)
- file_path
- file_name
- file_size
- mime_type
- is_active
- created_at
- updated_at

### budgets
- id (PK)
- user_id (FK → users)
- category_id (FK → categories, PROTECT)
- amount
- period_type (monthly/yearly)
- start_date
- end_date (nullable)
- is_active
- created_at
- updated_at
**Unique:** (user_id, category_id, period_type, start_date)

## Relationships

- User → UserProfile (1:1)
- User → Category (1:N, optional - system categories have no user)
- User → Account (1:N)
- User → Transaction (1:N)
- User → Tag (1:N)
- User → Budget (1:N)
- Account → Transaction (1:N, optional)
- Category → Transaction (1:N, PROTECT delete)
- Category → Budget (1:N, PROTECT delete)
- Transaction → Receipt (1:N)
- Transaction ↔ Tag (M:N through TransactionTag)

## Foreign Key Behaviors

- **CASCADE**: User deletions cascade to all related records
- **SET_NULL**: Account deletion sets transaction.account_id to NULL
- **PROTECT**: Cannot delete Category if it has transactions or budgets
