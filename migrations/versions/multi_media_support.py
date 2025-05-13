"""Add support for multiple media attachments

Revision ID: multi_media_support
Revises: 355f24925846
Create Date: 2025-05-15 14:22:07.767689

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError


# revision identifiers, used by Alembic.
revision = 'multi_media_support'
down_revision = '355f24925846'
branch_labels = None
depends_on = None


def upgrade():
    # Create complaint_media table for multiple attachments
    op.create_table('complaint_media',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('complaint_id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=256), nullable=False),
        sa.Column('media_type', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Migrate existing media data to the new table
    conn = op.get_bind()
    
    # Check if complaints table has media_path column
    has_media_columns = False
    try:
        conn.execute("SELECT media_path FROM complaints LIMIT 1")
        has_media_columns = True
    except:
        pass
    
    if has_media_columns:
        # Get all complaints with media
        result = conn.execute("SELECT id, media_path, media_type FROM complaints WHERE media_path IS NOT NULL")
        for row in result:
            # Insert into the new table
            conn.execute(
                "INSERT INTO complaint_media (complaint_id, file_path, media_type, created_at) "
                "SELECT id, media_path, media_type, created_at FROM complaints WHERE id = :id",
                {"id": row[0]}
            )


def downgrade():
    # Drop the new table
    op.drop_table('complaint_media') 