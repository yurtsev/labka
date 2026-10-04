from dishka import Provider, Scope, provide

from src.api.profile.service import ProfileService


class ProfileProvider(Provider):
    profile_service = provide(ProfileService, scope=Scope.REQUEST)
