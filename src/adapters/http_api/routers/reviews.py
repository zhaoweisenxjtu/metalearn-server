"""Reviews API router."""

from fastapi import APIRouter
from engine.db import dao_node, dao_review
from engine.core.sm2 import SM2Calculator
from ..schemas import ReviewCreate
from ..dependencies import not_found

router = APIRouter()


@router.post("")
def create_review(body: ReviewCreate):
    node = dao_node.get_node(body.node_id)
    if not node:
        not_found(f"Node {body.node_id} not found")
    result = SM2Calculator.compute(body.quality, node["ef"], node["interval"], node["repetitions"])
    dao_node.update_node(
        body.node_id,
        ef=result["ef"],
        interval=result["interval_days"],
        repetitions=result["repetitions"],
        next_review=result["next_review"],
    )
    review = dao_review.create_review(body.node_id, body.quality, result["ef"], result["interval_days"])
    return {"node": node["name"], **result, "review_id": review["id"]}


@router.get("/due")
def review_due(track_id: int | None = None, user_id: int | None = None):
    return dao_node.get_due_nodes(track_id, user_id)


@router.get("/stats")
def review_stats(track_id: int | None = None):
    return dao_review.get_review_stats(track_id)
