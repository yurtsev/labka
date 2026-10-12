from src.api.reviews.dto import ReviewCorrection, ReviewDecision
from src.api.reviews.schemas import ReviewCorrectRequest, ReviewCreateRequest
from src.core.grading.dto import Grade


def review_decision(body: ReviewCreateRequest) -> ReviewDecision:
    return ReviewDecision(
        verdict=body.verdict,
        grade=Grade(score=body.grade.score, passed=body.grade.passed),
        comment=body.comment or None,
    )


def review_correction(body: ReviewCorrectRequest) -> ReviewCorrection:
    return ReviewCorrection(
        grade=Grade(score=body.grade.score, passed=body.grade.passed),
        comment=body.comment or None,
    )
