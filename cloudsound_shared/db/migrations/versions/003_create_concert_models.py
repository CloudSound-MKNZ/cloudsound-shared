"""Create concert management models (Concert, ConcertArtist)

Revision ID: 003
Revises: 002
Create Date: 2025-11-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create concerts table
    op.create_table(
        'concerts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('location', sa.String(255), nullable=False),
        sa.Column('description', sa.String(2000), nullable=True),
        sa.Column('facebook_event_id', sa.String(255), nullable=True, unique=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_concerts_date', 'concerts', ['date'])
    op.create_index('ix_concerts_facebook_event_id', 'concerts', ['facebook_event_id'])
    
    # Create concert_artists junction table
    op.create_table(
        'concert_artists',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('concert_id', UUID(as_uuid=True), nullable=False),
        sa.Column('artist_id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['concert_id'], ['concerts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['artist_id'], ['artists.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('concert_id', 'artist_id', name='uq_concert_artist'),
    )
    op.create_index('ix_concert_artists_concert_id', 'concert_artists', ['concert_id'])
    op.create_index('ix_concert_artists_artist_id', 'concert_artists', ['artist_id'])


def downgrade() -> None:
    op.drop_index('ix_concert_artists_artist_id', table_name='concert_artists')
    op.drop_index('ix_concert_artists_concert_id', table_name='concert_artists')
    op.drop_table('concert_artists')
    
    op.drop_index('ix_concerts_facebook_event_id', table_name='concerts')
    op.drop_index('ix_concerts_date', table_name='concerts')
    op.drop_table('concerts')

