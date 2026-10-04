from dishka import Provider, Scope, provide

from src.core.access.service import AccessService


class AccessProvider(Provider):
    access_service = provide(AccessService, scope=Scope.REQUEST)
