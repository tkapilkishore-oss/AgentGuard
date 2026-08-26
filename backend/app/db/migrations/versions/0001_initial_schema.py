"""Initial Schema Migration for AgentGuard Phase 2

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-08-26 23:25:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. merchants
    op.create_table(
        'merchants',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. products
    op.create_table(
        'products',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('merchant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(), nullable=False),
        sa.Column('stock', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_merchant_id'), 'products', ['merchant_id'], unique=False)

    # 4. mandates
    op.create_table(
        'mandates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('budget_total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('budget_remaining', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('merchant_scope', sa.String(), nullable=True),
        sa.Column('category_scope', sa.String(), nullable=True),
        sa.Column('max_transaction_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mandates_user_id'), 'mandates', ['user_id'], unique=False)

    # 5. transactions
    op.create_table(
        'transactions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('mandate_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('merchant_id', sa.String(), nullable=False),
        sa.Column('product_id', sa.String(), nullable=False),
        sa.Column('claimed_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('authoritative_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('authoritative_total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('reason_code', sa.String(), nullable=False),
        sa.Column('nonce', sa.String(), nullable=False),
        sa.Column('idempotency_key', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['mandate_id'], ['mandates.id'], ),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transactions_mandate_id'), 'transactions', ['mandate_id'], unique=False)

    # 6. approvals
    op.create_table(
        'approvals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('transaction_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('approver_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_approvals_transaction_id'), 'approvals', ['transaction_id'], unique=False)

    # 7. idempotency_records
    op.create_table(
        'idempotency_records',
        sa.Column('idempotency_key', sa.String(), nullable=False),
        sa.Column('transaction_id', sa.String(), nullable=False),
        sa.Column('response_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ),
        sa.PrimaryKeyConstraint('idempotency_key')
    )
    op.create_index(op.f('ix_idempotency_records_transaction_id'), 'idempotency_records', ['transaction_id'], unique=False)

    # 8. audit_events
    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('transaction_id', sa.String(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('actor', sa.String(), nullable=False),
        sa.Column('payload_hash', sa.String(), nullable=False),
        sa.Column('prev_hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_events_transaction_id'), 'audit_events', ['transaction_id'], unique=False)

    # 9. audit_chain_state
    op.create_table(
        'audit_chain_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('last_hash', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('audit_chain_state')
    op.drop_index(op.f('ix_audit_events_transaction_id'), table_name='audit_events')
    op.drop_table('audit_events')
    op.drop_index(op.f('ix_idempotency_records_transaction_id'), table_name='idempotency_records')
    op.drop_table('idempotency_records')
    op.drop_index(op.f('ix_approvals_transaction_id'), table_name='approvals')
    op.drop_table('approvals')
    op.drop_index(op.f('ix_transactions_mandate_id'), table_name='transactions')
    op.drop_table('transactions')
    op.drop_index(op.f('ix_mandates_user_id'), table_name='mandates')
    op.drop_table('mandates')
    op.drop_index(op.f('ix_products_merchant_id'), table_name='products')
    op.drop_table('products')
    op.drop_table('merchants')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
