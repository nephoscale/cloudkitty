"""create invoice_details table

Revision ID: 3eecce93ff43
Revises: 792b438b663
Create Date: 2016-03-29 22:16:01.022645

"""

# revision identifiers, used by Alembic.
revision = '3eecce93ff43'
down_revision = '792b438b663'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('invoice_details',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('invoice_date', sa.DateTime(), nullable=False),
    sa.Column('invoice_period_from', sa.DateTime(), nullable=False),
    sa.Column('invoice_period_to', sa.DateTime(), nullable=False),
    sa.Column('tenant_id', sa.String(length=255), nullable=False),
    sa.Column('tenant_name', sa.String(length=255), nullable=False),
    sa.Column('invoice_id', sa.String(length=255), nullable=False),
    sa.Column('invoice_data', sa.Text(), nullable=False),
    sa.Column('total_cost', sa.Numeric(precision=13,scale=2), nullable=True),
    sa.Column('paid_cost', sa.Numeric(precision=13,scale=2), nullable=True),
    sa.Column('balance_cost', sa.Numeric(precision=13,scale=2), nullable=True),
    sa.Column('payment_status', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8',
    mysql_engine='InnoDB')

def downgrade():
    op.drop_table('invoice_details')
