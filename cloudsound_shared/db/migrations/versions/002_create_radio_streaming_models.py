"""Create radio streaming models (Artist, Track, RadioStation, StationTrack, PlaybackEvent)

Revision ID: 002
Revises: 001
Create Date: 2025-11-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create artists table
    op.create_table(
        'artists',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('genre', sa.String(100), nullable=True),
        sa.Column('bio', sa.String(2000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_artists_name', 'artists', ['name'])
    op.create_index('ix_artists_genre', 'artists', ['genre'])
    
    # Create tracks table
    op.create_table(
        'tracks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('artist_id', UUID(as_uuid=True), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_format', sa.String(10), nullable=False, server_default='mp3'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['artist_id'], ['artists.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_tracks_title', 'tracks', ['title'])
    op.create_index('ix_tracks_artist_id', 'tracks', ['artist_id'])
    
    # Create radio_stations table
    op.create_table(
        'radio_stations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('type', sa.String(50), nullable=False),  # 'upcoming', 'past', 'genre'
        sa.Column('genre', sa.String(100), nullable=True),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_radio_stations_name', 'radio_stations', ['name'])
    op.create_index('ix_radio_stations_type', 'radio_stations', ['type'])
    op.create_index('ix_radio_stations_genre', 'radio_stations', ['genre'])
    
    # Create station_tracks junction table
    op.create_table(
        'station_tracks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('station_id', UUID(as_uuid=True), nullable=False),
        sa.Column('track_id', UUID(as_uuid=True), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['station_id'], ['radio_stations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('station_id', 'track_id', name='uq_station_track'),
    )
    op.create_index('ix_station_tracks_station_id', 'station_tracks', ['station_id'])
    op.create_index('ix_station_tracks_track_id', 'station_tracks', ['track_id'])
    
    # Create playback_events table
    op.create_table(
        'playback_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('station_id', UUID(as_uuid=True), nullable=False),
        sa.Column('track_id', UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['station_id'], ['radio_stations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_playback_events_station_id', 'playback_events', ['station_id'])
    op.create_index('ix_playback_events_track_id', 'playback_events', ['track_id'])
    op.create_index('ix_playback_events_timestamp', 'playback_events', ['timestamp'])


def downgrade() -> None:
    op.drop_index('ix_playback_events_timestamp', table_name='playback_events')
    op.drop_index('ix_playback_events_track_id', table_name='playback_events')
    op.drop_index('ix_playback_events_station_id', table_name='playback_events')
    op.drop_table('playback_events')
    
    op.drop_index('ix_station_tracks_track_id', table_name='station_tracks')
    op.drop_index('ix_station_tracks_station_id', table_name='station_tracks')
    op.drop_table('station_tracks')
    
    op.drop_index('ix_radio_stations_genre', table_name='radio_stations')
    op.drop_index('ix_radio_stations_type', table_name='radio_stations')
    op.drop_index('ix_radio_stations_name', table_name='radio_stations')
    op.drop_table('radio_stations')
    
    op.drop_index('ix_tracks_artist_id', table_name='tracks')
    op.drop_index('ix_tracks_title', table_name='tracks')
    op.drop_table('tracks')
    
    op.drop_index('ix_artists_genre', table_name='artists')
    op.drop_index('ix_artists_name', table_name='artists')
    op.drop_table('artists')

