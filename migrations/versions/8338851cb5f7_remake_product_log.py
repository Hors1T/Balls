"""remake product_log

Revision ID: 8338851cb5f7
Revises: 608dd28df890
Create Date: 2025-03-19 22:22:53.350860

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8338851cb5f7'
down_revision = '608dd28df890'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('product_log', schema=None) as batch_op:
        batch_op.alter_column('action',
               existing_type=sa.VARCHAR(length=50),
               type_=sa.Text(),
               existing_nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('product_log', schema=None) as batch_op:
        batch_op.alter_column('action',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(length=50),
               existing_nullable=False)

    # ### end Alembic commands ###
