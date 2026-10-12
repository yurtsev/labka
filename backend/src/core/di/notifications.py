from dishka import Provider, Scope, provide

from src.api.notifications.service import NotificationsService
from src.core.notifications.service import NotificationService


class NotificationsProvider(Provider):
    notification_service = provide(NotificationService, scope=Scope.REQUEST)
    notifications_service = provide(NotificationsService, scope=Scope.REQUEST)
