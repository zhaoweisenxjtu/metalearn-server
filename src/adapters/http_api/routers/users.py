"""Users API router."""

from fastapi import APIRouter
from engine.db import dao_user
from ..dependencies import not_found

router = APIRouter()


@router.post("")
def create_user(name: str, display_name: str = ""):
    return dao_user.create_user(name, display_name or name)


@router.get("")
def list_users():
    return dao_user.list_users()


@router.get("/{user_id}")
def get_user(user_id: int):
    user = dao_user.get_user(user_id)
    if not user:
        not_found(f"User {user_id} not found")
    return user


@router.delete("/{user_id}")
def delete_user(user_id: int):
    ok = dao_user.delete_user(user_id)
    if not ok:
        not_found(f"User {user_id} not found")
    return {"deleted": True}
