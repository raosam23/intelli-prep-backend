"""apply delete cascades to foreign keys

Revision ID: b7a653634da7
Revises: bea424559345
Create Date: 2026-03-27 00:42:32.179027

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7a653634da7'
down_revision: Union[str, Sequence[str], None] = 'bea424559345'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("resumes_user_id_fkey", "resumes", type_="foreignkey")
    op.create_foreign_key(
        "resumes_user_id_fkey",
        "resumes",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("job_applications_user_id_fkey", "job_applications", type_="foreignkey")
    op.create_foreign_key(
        "job_applications_user_id_fkey",
        "job_applications",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("job_applications_resume_id_fkey", "job_applications", type_="foreignkey")
    op.create_foreign_key(
        "job_applications_resume_id_fkey",
        "job_applications",
        "resumes",
        ["resume_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("interview_sessions_job_application_id_fkey", "interview_sessions", type_="foreignkey")
    op.create_foreign_key(
        "interview_sessions_job_application_id_fkey",
        "interview_sessions",
        "job_applications",
        ["job_application_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("questions_session_id_fkey", "questions", type_="foreignkey")
    op.create_foreign_key(
        "questions_session_id_fkey",
        "questions",
        "interview_sessions",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("questions_follow_up_to_fkey", "questions", type_="foreignkey")
    op.create_foreign_key(
        "questions_follow_up_to_fkey",
        "questions",
        "questions",
        ["follow_up_to"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("answers_question_id_fkey", "answers", type_="foreignkey")
    op.create_foreign_key(
        "answers_question_id_fkey",
        "answers",
        "questions",
        ["question_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("answers_session_id_fkey", "answers", type_="foreignkey")
    op.create_foreign_key(
        "answers_session_id_fkey",
        "answers",
        "interview_sessions",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("evaluations_session_id_fkey", "evaluations", type_="foreignkey")
    op.create_foreign_key(
        "evaluations_session_id_fkey",
        "evaluations",
        "interview_sessions",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("evaluations_session_id_fkey", "evaluations", type_="foreignkey")
    op.create_foreign_key(
        "evaluations_session_id_fkey",
        "evaluations",
        "interview_sessions",
        ["session_id"],
        ["id"],
    )

    op.drop_constraint("answers_session_id_fkey", "answers", type_="foreignkey")
    op.create_foreign_key(
        "answers_session_id_fkey",
        "answers",
        "interview_sessions",
        ["session_id"],
        ["id"],
    )

    op.drop_constraint("answers_question_id_fkey", "answers", type_="foreignkey")
    op.create_foreign_key(
        "answers_question_id_fkey",
        "answers",
        "questions",
        ["question_id"],
        ["id"],
    )

    op.drop_constraint("questions_follow_up_to_fkey", "questions", type_="foreignkey")
    op.create_foreign_key(
        "questions_follow_up_to_fkey",
        "questions",
        "questions",
        ["follow_up_to"],
        ["id"],
    )

    op.drop_constraint("questions_session_id_fkey", "questions", type_="foreignkey")
    op.create_foreign_key(
        "questions_session_id_fkey",
        "questions",
        "interview_sessions",
        ["session_id"],
        ["id"],
    )

    op.drop_constraint("interview_sessions_job_application_id_fkey", "interview_sessions", type_="foreignkey")
    op.create_foreign_key(
        "interview_sessions_job_application_id_fkey",
        "interview_sessions",
        "job_applications",
        ["job_application_id"],
        ["id"],
    )

    op.drop_constraint("job_applications_resume_id_fkey", "job_applications", type_="foreignkey")
    op.create_foreign_key(
        "job_applications_resume_id_fkey",
        "job_applications",
        "resumes",
        ["resume_id"],
        ["id"],
    )

    op.drop_constraint("job_applications_user_id_fkey", "job_applications", type_="foreignkey")
    op.create_foreign_key(
        "job_applications_user_id_fkey",
        "job_applications",
        "users",
        ["user_id"],
        ["id"],
    )

    op.drop_constraint("resumes_user_id_fkey", "resumes", type_="foreignkey")
    op.create_foreign_key(
        "resumes_user_id_fkey",
        "resumes",
        "users",
        ["user_id"],
        ["id"],
    )
