from dishka import Provider, Scope, provide

from src.api.feed.service import FeedService


class FeedProvider(Provider):
    feed_service = provide(FeedService, scope=Scope.REQUEST)
