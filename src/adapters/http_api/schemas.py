"""Pydantic schemas for API request/response."""

from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    name: str
    display_name: str = ""


class TrackCreate(BaseModel):
    user_id: int
    name: str
    type: str = "applied"
    priority: int = 3


class TrackUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None


class NodeCreate(BaseModel):
    track_id: int
    name: str
    description: str = ""
    importance: int = 3
    level: int = 1
    parent: Optional[int] = None


class NodeUpdate(BaseModel):
    name: Optional[str] = None
    level: Optional[int] = None
    status: Optional[str] = None


class ReviewCreate(BaseModel):
    node_id: int
    quality: int


class AssessmentCreate(BaseModel):
    user_id: int
    track_id: int
    after: int
    before: Optional[int] = None
    node: Optional[int] = None
    methods: list[str] = []
    duration: int = 0
    notes: str = ""


class JournalCreate(BaseModel):
    user_id: int
    date: Optional[str] = None
    focus: int = 0
    diffuse: int = 0
    topics: list[str] = []
    methods: list[str] = []
    highlights: str = ""
    struggles: str = ""
    tomorrow: str = ""
