from dishka import Provider, Scope, provide

from src.api.notifications.dispatcher import RealtimeDispatcher
from src.api.notifications.service import NotificationsService, RealtimeService
from src.config import cfg
from src.core.notifications.service import NotificationService
from src.core.realtime.hub import RealtimeHub
from src.core.realtime.listener import PostgresListener


class NotificationsProvider(Provider):
    notification_service = provide(NotificationService, scope=Scope.REQUEST)
    notifications_service = provide(NotificationsService, scope=Scope.REQUEST)
    hub = provide(RealtimeHub, scope=Scope.APP)
    realtime_service = provide(RealtimeService, scope=Scope.APP)
    dispatcher = provide(RealtimeDispatcher, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def get_listener(self, dispatcher: RealtimeDispatcher) -> PostgresListener:
        return PostgresListener(
            cfg.database.asyncpg_dsn,
            {
                "notifications": dispatcher.on_notification,
                "session_revoked": dispatcher.on_session_revoked,
            },
            dispatcher.resync,
            keepalive_seconds=cfg.notifications.websocket_ping_seconds,
        )
