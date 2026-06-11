"""Assessments API router."""

from fastapi import APIRouter
from engine.db import dao_assessment
from ..schemas import AssessmentCreate

router = APIRouter()


@router.post("")
def log_assessment(body: AssessmentCreate):
    return dao_assessment.log_assessment(
        body.user_id, body.track_id, body.after,
        body.node, body.before, body.methods,
        body.duration, body.notes,
    )


@router.get("")
def list_assessments(track_id: int | None = None, user_id: int | None = None):
    return dao_assessment.list_assessments(track_id, user_id)
