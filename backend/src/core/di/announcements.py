from dishka import Provider, Scope, provide

from src.api.announcements.service import AnnouncementService


class AnnouncementsProvider(Provider):
    announcement_service = provide(AnnouncementService, scope=Scope.REQUEST)
