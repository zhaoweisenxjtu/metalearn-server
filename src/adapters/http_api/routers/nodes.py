"""Knowledge Nodes API router."""

from fastapi import APIRouter
from engine.db import dao_node
from ..dependencies import not_found

router = APIRouter()


@router.post("")
def add_node(track_id: int, name: str,
             description: str = "", importance: int = 3,
             level: int = 1, parent: int | None = None):
    return dao_node.add_node(track_id, name, description, parent, importance, level)


@router.get("")
def list_nodes(track_id: int | None = None, status: str | None = None):
    return dao_node.list_nodes(track_id, status)


@router.get("/{node_id}")
def get_node(node_id: int):
    node = dao_node.get_node(node_id)
    if not node:
        not_found(f"Node {node_id} not found")
    return node


@router.patch("/{node_id}")
def update_node(node_id: int, name: str | None = None,
                level: int | None = None, status: str | None = None):
    updates = {}
    if name is not None: updates["name"] = name
    if level is not None: updates["current_level"] = level
    if status is not None: updates["status"] = status
    node = dao_node.update_node(node_id, **updates)
    if not node:
        not_found(f"Node {node_id} not found")
    return node


@router.delete("/{node_id}")
def delete_node(node_id: int):
    ok = dao_node.delete_node(node_id)
    if not ok:
        not_found(f"Node {node_id} not found")
    return {"deleted": True}
