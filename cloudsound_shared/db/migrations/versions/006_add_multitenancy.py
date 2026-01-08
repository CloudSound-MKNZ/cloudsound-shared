"""Add multitenancy support.

Revision ID: 006_add_multitenancy
Revises: 005_add_performance_indexes
Create Date: 2026-01-08

This migration adds:
1. Tenants table for managing tenants
2. tenant_id column to existing tables (for row-level multitenancy)
3. Composite unique constraints (per-tenant uniqueness)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_multitenancy'
down_revision = '005_add_performance_indexes'
branch_labels = None
depends_on = None

# Default tenant ID for migrating existing data
DEFAULT_TENANT_ID = 'aaaaaaaa-0000-0000-0000-000000000001'


def upgrade() -> None:
    # ==========================================================================
    # 1. Create tenants table
    # ==========================================================================
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('domain', sa.String(255), nullable=True),
        sa.Column('schema_name', sa.String(100), nullable=True),
        sa.Column('database_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('plan', sa.String(50), nullable=False, server_default='free'),
        sa.Column('settings', sa.String(5000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create indexes for tenants table
    op.create_index('ix_tenants_slug', 'tenants', ['slug'], unique=True)
    op.create_index('ix_tenants_domain', 'tenants', ['domain'], unique=True)
    op.create_index('ix_tenants_schema_name', 'tenants', ['schema_name'], unique=True)
    op.create_index('ix_tenants_is_active', 'tenants', ['is_active'])
    
    # Create default tenant (for migration of existing data)
    op.execute(f"""
        INSERT INTO tenants (id, slug, name, is_active, plan, created_at, updated_at)
        VALUES (
            '{DEFAULT_TENANT_ID}',
            'default',
            'Default Tenant',
            true,
            'enterprise',
            NOW(),
            NOW()
        )
        ON CONFLICT DO NOTHING
    """)
    
    # ==========================================================================
    # 2. Add tenant_id to artists table
    # ==========================================================================
    # Drop old unique constraint on name
    op.drop_constraint('artists_name_key', 'artists', type_='unique')
    
    # Add tenant_id column
    op.add_column('artists', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Populate with default tenant
    op.execute(f"UPDATE artists SET tenant_id = '{DEFAULT_TENANT_ID}' WHERE tenant_id IS NULL")
    
    # Make non-nullable
    op.alter_column('artists', 'tenant_id', nullable=False)
    
    # Create indexes and constraints
    op.create_index('ix_artists_tenant_id', 'artists', ['tenant_id'])
    op.create_unique_constraint('uq_artists_tenant_name', 'artists', ['tenant_id', 'name'])
    
    # ==========================================================================
    # 3. Add tenant_id to radio_stations table
    # ==========================================================================
    # Drop old unique constraint on name
    op.drop_constraint('radio_stations_name_key', 'radio_stations', type_='unique')
    
    # Add tenant_id column
    op.add_column('radio_stations', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Populate with default tenant
    op.execute(f"UPDATE radio_stations SET tenant_id = '{DEFAULT_TENANT_ID}' WHERE tenant_id IS NULL")
    
    # Make non-nullable
    op.alter_column('radio_stations', 'tenant_id', nullable=False)
    
    # Create indexes and constraints
    op.create_index('ix_radio_stations_tenant_id', 'radio_stations', ['tenant_id'])
    op.create_unique_constraint('uq_radio_stations_tenant_name', 'radio_stations', ['tenant_id', 'name'])
    
    # ==========================================================================
    # 4. Add tenant_id to tracks table
    # ==========================================================================
    op.add_column('tracks', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Populate with default tenant
    op.execute(f"UPDATE tracks SET tenant_id = '{DEFAULT_TENANT_ID}' WHERE tenant_id IS NULL")
    
    # Make non-nullable
    op.alter_column('tracks', 'tenant_id', nullable=False)
    
    # Create indexes and constraints
    op.create_index('ix_tracks_tenant_id', 'tracks', ['tenant_id'])
    op.create_unique_constraint('uq_tracks_tenant_file_path', 'tracks', ['tenant_id', 'file_path'])
    
    # ==========================================================================
    # 5. Add tenant_id to concerts table
    # ==========================================================================
    # Drop old unique constraint on facebook_event_id (if exists)
    try:
        op.drop_constraint('concerts_facebook_event_id_key', 'concerts', type_='unique')
    except Exception:
        pass  # Constraint might not exist
    
    op.add_column('concerts', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Populate with default tenant
    op.execute(f"UPDATE concerts SET tenant_id = '{DEFAULT_TENANT_ID}' WHERE tenant_id IS NULL")
    
    # Make non-nullable
    op.alter_column('concerts', 'tenant_id', nullable=False)
    
    # Create indexes and constraints
    op.create_index('ix_concerts_tenant_id', 'concerts', ['tenant_id'])
    op.create_unique_constraint('uq_concerts_tenant_facebook_event', 'concerts', ['tenant_id', 'facebook_event_id'])
    
    # ==========================================================================
    # 6. Add tenant_id to playback_events table
    # ==========================================================================
    op.add_column('playback_events', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add timestamp columns if they don't exist (model was updated to include TimestampMixin)
    try:
        op.add_column('playback_events', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
        op.add_column('playback_events', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    except Exception:
        pass  # Columns might already exist
    
    # Populate with default tenant
    op.execute(f"UPDATE playback_events SET tenant_id = '{DEFAULT_TENANT_ID}' WHERE tenant_id IS NULL")
    
    # Make non-nullable
    op.alter_column('playback_events', 'tenant_id', nullable=False)
    
    # Create indexes for analytics queries
    op.create_index('ix_playback_events_tenant_id', 'playback_events', ['tenant_id'])
    op.create_index('ix_playback_events_tenant_timestamp', 'playback_events', ['tenant_id', 'timestamp'])
    op.create_index('ix_playback_events_tenant_station', 'playback_events', ['tenant_id', 'station_id'])


def downgrade() -> None:
    # ==========================================================================
    # Remove tenant_id from playback_events
    # ==========================================================================
    op.drop_index('ix_playback_events_tenant_station', table_name='playback_events')
    op.drop_index('ix_playback_events_tenant_timestamp', table_name='playback_events')
    op.drop_index('ix_playback_events_tenant_id', table_name='playback_events')
    op.drop_column('playback_events', 'tenant_id')
    
    # ==========================================================================
    # Remove tenant_id from concerts
    # ==========================================================================
    op.drop_constraint('uq_concerts_tenant_facebook_event', 'concerts', type_='unique')
    op.drop_index('ix_concerts_tenant_id', table_name='concerts')
    op.drop_column('concerts', 'tenant_id')
    # Restore global unique constraint
    op.create_unique_constraint('concerts_facebook_event_id_key', 'concerts', ['facebook_event_id'])
    
    # ==========================================================================
    # Remove tenant_id from tracks
    # ==========================================================================
    op.drop_constraint('uq_tracks_tenant_file_path', 'tracks', type_='unique')
    op.drop_index('ix_tracks_tenant_id', table_name='tracks')
    op.drop_column('tracks', 'tenant_id')
    
    # ==========================================================================
    # Remove tenant_id from radio_stations
    # ==========================================================================
    op.drop_constraint('uq_radio_stations_tenant_name', 'radio_stations', type_='unique')
    op.drop_index('ix_radio_stations_tenant_id', table_name='radio_stations')
    op.drop_column('radio_stations', 'tenant_id')
    # Restore global unique constraint
    op.create_unique_constraint('radio_stations_name_key', 'radio_stations', ['name'])
    
    # ==========================================================================
    # Remove tenant_id from artists
    # ==========================================================================
    op.drop_constraint('uq_artists_tenant_name', 'artists', type_='unique')
    op.drop_index('ix_artists_tenant_id', table_name='artists')
    op.drop_column('artists', 'tenant_id')
    # Restore global unique constraint
    op.create_unique_constraint('artists_name_key', 'artists', ['name'])
    
    # ==========================================================================
    # Drop tenants table
    # ==========================================================================
    op.drop_index('ix_tenants_is_active', table_name='tenants')
    op.drop_index('ix_tenants_schema_name', table_name='tenants')
    op.drop_index('ix_tenants_domain', table_name='tenants')
    op.drop_index('ix_tenants_slug', table_name='tenants')
    op.drop_table('tenants')
