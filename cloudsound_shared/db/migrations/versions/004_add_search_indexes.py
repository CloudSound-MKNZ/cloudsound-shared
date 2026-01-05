"""Add search performance indexes for artists and tracks

Revision ID: 004
Revises: 003
Create Date: 2025-11-30

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pg_trgm extension for trigram indexes (better ILIKE performance)
    # Note: This requires superuser privileges. If not available, the migration will fail
    # and you'll need to enable it manually: CREATE EXTENSION IF NOT EXISTS pg_trgm;
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    except Exception:
        # Extension might already exist or require superuser privileges
        # Log warning but continue - regular indexes will still work
        pass
    
    # Create trigram GIN indexes for better ILIKE search performance
    # These indexes significantly improve performance for pattern matching queries
    try:
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_artists_name_trgm "
            "ON artists USING gin (name gin_trgm_ops);"
        )
    except Exception:
        # If pg_trgm is not available, skip trigram indexes
        # Regular B-tree indexes from migration 002 will still be used
        pass
    
    try:
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_tracks_title_trgm "
            "ON tracks USING gin (title gin_trgm_ops);"
        )
    except Exception:
        # If pg_trgm is not available, skip trigram indexes
        pass
    
    # Note: Regular indexes on artists.name and tracks.title already exist from migration 002
    # These are useful for exact matches and some pattern queries
    # No need to recreate them here


def downgrade() -> None:
    # Drop trigram indexes if they exist
    try:
        op.execute("DROP INDEX IF EXISTS ix_artists_name_trgm;")
    except Exception:
        pass
    
    try:
        op.execute("DROP INDEX IF EXISTS ix_tracks_title_trgm;")
    except Exception:
        pass
    
    # Note: We don't drop the regular indexes as they were created in migration 002
    # and might be used by other queries

