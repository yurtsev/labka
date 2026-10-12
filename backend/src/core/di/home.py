from dishka import Provider, Scope, provide

from src.api.home.service import HomeService


class HomeProvider(Provider):
    home_service = provide(HomeService, scope=Scope.REQUEST)
