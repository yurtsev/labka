"""reminder_per_deadline

Revision ID: 1f05c639a677
Revises: 8a0b3312bc5c
Create Date: 2026-10-12 23:10:04.734159

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f05c639a677'
down_revision: Union[str, Sequence[str], None] = '8a0b3312bc5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Напоминание о дедлайне уникально по «студент + задание + срок»: после переноса срока
    приходит новое."""
    op.drop_index('uq_notifications_deadline_reminder', table_name='notifications', postgresql_where=sa.text("type = 'deadline_reminder'"))
    op.create_index('uq_notifications_deadline_reminder', 'notifications', ['user_id', sa.literal_column("(data ->> 'assignment_id')"), sa.literal_column("(data ->> 'deadline_at')")], unique=True, postgresql_where=sa.text("type = 'deadline_reminder'"))


def downgrade() -> None:
    """Откат возможен, пока по каждому заданию у студента не больше одного напоминания."""
    repeated = op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM notifications WHERE type = 'deadline_reminder'"
            " GROUP BY user_id, data ->> 'assignment_id' HAVING count(*) > 1)"
        )
    )
    if repeated:
        raise NotImplementedError("Есть повторные напоминания после переноса срока: откат их удалил бы")
    op.drop_index('uq_notifications_deadline_reminder', table_name='notifications', postgresql_where=sa.text("type = 'deadline_reminder'"))
    op.create_index('uq_notifications_deadline_reminder', 'notifications', ['user_id', sa.literal_column("(data ->> 'assignment_id')")], unique=True, postgresql_where=sa.text("type = 'deadline_reminder'"))
