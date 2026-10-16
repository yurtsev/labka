"""drop final grades

Revision ID: 84bb9ee4e02a
Revises: 1f05c639a677
Create Date: 2026-10-16 06:31:39.997601

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '84bb9ee4e02a'
down_revision: Union[str, Sequence[str], None] = '1f05c639a677'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TYPES = (
    "course_added",
    "assignment_created",
    "assignment_updated",
    "material_added",
    "announcement_created",
    "schedule_changed",
    "submission_reviewed",
    "grade_changed",
    "deadline_reminder",
    "submission_created",
    "exam_assigned",
    "exam_changed",
)
OLD_TYPES = (*TYPES, "final_result_set")


def _type_check(types: tuple[str, ...]) -> str:
    return "type IN (" + ", ".join(f"'{item}'" for item in types) + ")"


def upgrade() -> None:
    """Итоговые результаты убраны: таблица и уведомления «итоговый результат выставлен».

    Данные итоговых и их уведомлений удаляются безвозвратно; зачёты и экзамены остаются.
    """
    op.execute("DELETE FROM notifications WHERE type = 'final_result_set'")
    op.drop_constraint('notificationtype', 'notifications', type_='check')
    op.create_check_constraint('notificationtype', 'notifications', _type_check(TYPES))
    op.drop_index(op.f('ix_final_grades_student_id'), table_name='final_grades')
    op.drop_table('final_grades')


def downgrade() -> None:
    """Возвращает структуру; удалённые итоговые и их уведомления откат не восстанавливает."""
    op.drop_constraint('notificationtype', 'notifications', type_='check')
    op.create_check_constraint('notificationtype', 'notifications', _type_check(OLD_TYPES))
    op.create_table('final_grades',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('course_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('student_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('grade', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('is_passed', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.CheckConstraint('grade IS NULL OR grade >= 2 AND grade <= 5', name=op.f('ck_final_grades_grade_range')),
    sa.CheckConstraint('(grade IS NULL) <> (is_passed IS NULL)', name=op.f('ck_final_grades_single_result')),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], name=op.f('fk_final_grades_course_id_courses'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['student_id'], ['users.id'], name=op.f('fk_final_grades_student_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_final_grades')),
    sa.UniqueConstraint('course_id', 'student_id', name=op.f('uq_final_grades_course_id_student_id'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('ix_final_grades_student_id'), 'final_grades', ['student_id'], unique=False)
