"""empty message

Revision ID: 2e32e818ef03
Revises: None
Create Date: 2014-03-24 10:35:53.348617

"""

# revision identifiers, used by Alembic.
revision = '2e32e818ef03'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('solution',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('challenge_id', sa.Integer(), nullable=True),
    sa.Column('value', sa.String(), nullable=True),
    sa.Column('user', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['challenge_id'], ['challenge.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('solution')
    ### end Alembic commands ###
