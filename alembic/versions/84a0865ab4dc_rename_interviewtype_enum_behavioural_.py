"""rename interviewtype enum BEHAVIOURAL to BEHAVIORAL

Revision ID: 84a0865ab4dc
Revises: b7a653634da7
Create Date: 2026-04-01 01:41:38.723022

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '84a0865ab4dc'
down_revision: Union[str, Sequence[str], None] = 'b7a653634da7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON e.enumtypid = t.oid
                WHERE t.typname = 'interviewtype' AND e.enumlabel = 'BEHAVIOURAL'
            ) AND NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON e.enumtypid = t.oid
                WHERE t.typname = 'interviewtype' AND e.enumlabel = 'BEHAVIORAL'
            ) THEN
                ALTER TYPE interviewtype RENAME VALUE 'BEHAVIOURAL' TO 'BEHAVIORAL';
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON e.enumtypid = t.oid
                WHERE t.typname = 'interviewtype' AND e.enumlabel = 'BEHAVIORAL'
            ) AND NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON e.enumtypid = t.oid
                WHERE t.typname = 'interviewtype' AND e.enumlabel = 'BEHAVIOURAL'
            ) THEN
                ALTER TYPE interviewtype RENAME VALUE 'BEHAVIORAL' TO 'BEHAVIOURAL';
            END IF;
        END
        $$;
        """
    )
