"""final_grade_credit_result

Revision ID: bc413125e4ab
Revises: 092bee36f3fd
Create Date: 2026-10-12 20:49:10.622831

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc413125e4ab'
down_revision: Union[str, Sequence[str], None] = '092bee36f3fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Зачёт хранится как `is_passed`, дифф. зачёт и экзамен — как `grade`: задано одно из двух."""
    op.add_column('final_grades', sa.Column('is_passed', sa.Boolean(), nullable=True))
    op.alter_column('final_grades', 'grade', existing_type=sa.INTEGER(), nullable=True)
    op.drop_constraint('grade_range', 'final_grades', type_='check')
    op.create_check_constraint(
        'grade_range', 'final_grades', 'grade IS NULL OR grade BETWEEN 2 AND 5'
    )
    op.create_check_constraint(
        'single_result', 'final_grades', '(grade IS NULL) <> (is_passed IS NULL)'
    )


def downgrade() -> None:
    """Откат потерял бы результаты зачётов."""
    raise NotImplementedError("Откат удалит результаты «зачтено / не зачтено»")
