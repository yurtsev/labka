"""notification_delivery

Revision ID: 8a0b3312bc5c
Revises: bc413125e4ab
Create Date: 2026-10-12 21:53:26.290079

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a0b3312bc5c'
down_revision: Union[str, Sequence[str], None] = 'bc413125e4ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_TYPES = (
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
)
NEW_TYPES = (*OLD_TYPES, "exam_assigned", "exam_changed", "final_result_set")


def _type_check(types: tuple[str, ...]) -> str:
    return "type IN (" + ", ".join(f"'{item}'" for item in types) + ")"


def upgrade() -> None:
    """Доставка уведомлений: ключ дедупликации, индексы и сообщения PostgreSQL о событиях.

    Триггеры шлют `NOTIFY` внутри транзакции, поэтому слушатели получают событие только
    после коммита: о новом или обновлённом уведомлении (`notifications`) и об отозванной
    сессии (`session_revoked`). Payload — короткий JSON, не больше лимита NOTIFY.
    """
    op.add_column('notifications', sa.Column('dedup_key', sa.String(), nullable=True))
    op.create_index('ix_notifications_unread', 'notifications', ['user_id'], unique=False, postgresql_where=sa.text('NOT is_read'))
    op.create_index('uq_notifications_unread_dedup', 'notifications', ['user_id', 'dedup_key'], unique=True, postgresql_where=sa.text('NOT is_read AND dedup_key IS NOT NULL'))
    op.drop_constraint('notificationtype', 'notifications', type_='check')
    op.create_check_constraint('notificationtype', 'notifications', _type_check(NEW_TYPES))
    op.execute(
        """
        CREATE FUNCTION notify_notification_created() RETURNS trigger AS $$
        BEGIN
            PERFORM pg_notify(
                'notifications',
                json_build_object('id', NEW.id, 'user_id', NEW.user_id)::text
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER notifications_notify AFTER INSERT OR UPDATE OF data ON notifications"
        " FOR EACH ROW EXECUTE FUNCTION notify_notification_created()"
    )
    op.execute(
        """
        CREATE FUNCTION notify_session_revoked() RETURNS trigger AS $$
        BEGIN
            PERFORM pg_notify('session_revoked', NEW.id::text);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER sessions_revoked_notify AFTER UPDATE OF revoked_at ON sessions"
        " FOR EACH ROW WHEN (OLD.revoked_at IS NULL AND NEW.revoked_at IS NOT NULL)"
        " EXECUTE FUNCTION notify_session_revoked()"
    )


def downgrade() -> None:
    """Откат без потерь возможен, пока нет уведомлений новых типов."""
    new_types = op.get_bind().scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM notifications WHERE type IN :types)").bindparams(
            sa.bindparam("types", expanding=True)
        ),
        {"types": list(NEW_TYPES[len(OLD_TYPES):])},
    )
    if new_types:
        raise NotImplementedError("Есть уведомления новых типов: откат их удалил бы")
    op.execute("DROP TRIGGER sessions_revoked_notify ON sessions")
    op.execute("DROP FUNCTION notify_session_revoked()")
    op.execute("DROP TRIGGER notifications_notify ON notifications")
    op.execute("DROP FUNCTION notify_notification_created()")
    op.drop_constraint('notificationtype', 'notifications', type_='check')
    op.create_check_constraint('notificationtype', 'notifications', _type_check(OLD_TYPES))
    op.drop_index('uq_notifications_unread_dedup', table_name='notifications', postgresql_where=sa.text('NOT is_read AND dedup_key IS NOT NULL'))
    op.drop_index('ix_notifications_unread', table_name='notifications', postgresql_where=sa.text('NOT is_read'))
    op.drop_column('notifications', 'dedup_key')
