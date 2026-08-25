from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: UUID
    full_name: str
    completed_trainings: int
    average_progress: int
    has_avatar: bool
    avatar_updated_at: datetime | None
    is_current_user: bool


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]
    current_user: LeaderboardEntry
