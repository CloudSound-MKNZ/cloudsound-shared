"""Add performance indexes for common query patterns

Revision ID: 005
Revises: 004
Create Date: 2026-01-06

This migration adds indexes to optimize frequently used query patterns:
- Concert date filtering (upcoming concerts)
- Playback event timestamps
- Radio station active status
- Foreign key relationships
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Concert indexes
    # Index for filtering upcoming concerts (date-based queries)
    op.create_index(
        'ix_concerts_date',
        'concerts',
        ['date'],
        unique=False,
        if_not_exists=True,
    )
    
    # Composite index for concerts with location filtering
    op.create_index(
        'ix_concerts_date_location',
        'concerts',
        ['date', 'location'],
        unique=False,
        if_not_exists=True,
    )
    
    # Index for Facebook event lookup
    op.create_index(
        'ix_concerts_facebook_event_id',
        'concerts',
        ['facebook_event_id'],
        unique=False,
        if_not_exists=True,
    )
    
    # Radio station indexes
    # Index for filtering active stations
    op.create_index(
        'ix_radio_stations_is_active',
        'radio_stations',
        ['is_active'],
        unique=False,
        if_not_exists=True,
    )
    
    # Index for station type queries
    op.create_index(
        'ix_radio_stations_type',
        'radio_stations',
        ['type'],
        unique=False,
        if_not_exists=True,
    )
    
    # Composite index for active stations by type
    op.create_index(
        'ix_radio_stations_active_type',
        'radio_stations',
        ['is_active', 'type'],
        unique=False,
        if_not_exists=True,
    )
    
    # Index for genre-based queries
    op.create_index(
        'ix_radio_stations_genre',
        'radio_stations',
        ['genre'],
        unique=False,
        if_not_exists=True,
    )
    
    # Track indexes
    # Index for artist-based track lookups
    op.create_index(
        'ix_tracks_artist_id',
        'tracks',
        ['artist_id'],
        unique=False,
        if_not_exists=True,
    )
    
    # Index for source-based queries (e.g., all YouTube tracks)
    op.create_index(
        'ix_tracks_source_type',
        'tracks',
        ['source_type'],
        unique=False,
        if_not_exists=True,
    )
    
    # Playback event indexes
    # Index for time-based analytics queries
    op.create_index(
        'ix_playback_events_started_at',
        'playback_events',
        ['started_at'],
        unique=False,
        if_not_exists=True,
    )
    
    # Index for track-specific analytics
    op.create_index(
        'ix_playback_events_track_id',
        'playback_events',
        ['track_id'],
        unique=False,
        if_not_exists=True,
    )
    
    # Index for station-specific analytics
    op.create_index(
        'ix_playback_events_station_id',
        'playback_events',
        ['station_id'],
        unique=False,
        if_not_exists=True,
    )
    
    # Composite index for station + time analytics
    op.create_index(
        'ix_playback_events_station_time',
        'playback_events',
        ['station_id', 'started_at'],
        unique=False,
        if_not_exists=True,
    )
    
    # Station tracks indexes
    # Index for position-based ordering
    op.create_index(
        'ix_station_tracks_position',
        'station_tracks',
        ['station_id', 'position'],
        unique=False,
        if_not_exists=True,
    )
    
    # Concert artists indexes
    # Index for artist-based concert lookups
    op.create_index(
        'ix_concert_artists_artist_id',
        'concert_artists',
        ['artist_id'],
        unique=False,
        if_not_exists=True,
    )
    
    # Artist indexes
    # Index for genre-based queries
    op.create_index(
        'ix_artists_genre',
        'artists',
        ['genre'],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    # Drop all indexes created in this migration
    op.drop_index('ix_concerts_date', table_name='concerts', if_exists=True)
    op.drop_index('ix_concerts_date_location', table_name='concerts', if_exists=True)
    op.drop_index('ix_concerts_facebook_event_id', table_name='concerts', if_exists=True)
    op.drop_index('ix_radio_stations_is_active', table_name='radio_stations', if_exists=True)
    op.drop_index('ix_radio_stations_type', table_name='radio_stations', if_exists=True)
    op.drop_index('ix_radio_stations_active_type', table_name='radio_stations', if_exists=True)
    op.drop_index('ix_radio_stations_genre', table_name='radio_stations', if_exists=True)
    op.drop_index('ix_tracks_artist_id', table_name='tracks', if_exists=True)
    op.drop_index('ix_tracks_source_type', table_name='tracks', if_exists=True)
    op.drop_index('ix_playback_events_started_at', table_name='playback_events', if_exists=True)
    op.drop_index('ix_playback_events_track_id', table_name='playback_events', if_exists=True)
    op.drop_index('ix_playback_events_station_id', table_name='playback_events', if_exists=True)
    op.drop_index('ix_playback_events_station_time', table_name='playback_events', if_exists=True)
    op.drop_index('ix_station_tracks_position', table_name='station_tracks', if_exists=True)
    op.drop_index('ix_concert_artists_artist_id', table_name='concert_artists', if_exists=True)
    op.drop_index('ix_artists_genre', table_name='artists', if_exists=True)

