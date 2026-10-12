from dishka import Provider, Scope, provide

from src.api.reviews.service import ReviewService


class ReviewsProvider(Provider):
    review_service = provide(ReviewService, scope=Scope.REQUEST)
