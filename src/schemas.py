from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

# схемы для юзеров
class UserCreate(BaseModel):
    email: str
    password: str = Field(..., max_length=50)

class UserResponse(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True


# схемы для ссылок
class LinkCreate(BaseModel):
    original_url: str
    # кастомный алиас
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None

class LinkUpdate(BaseModel):
    original_url: str

class LinkResponse(BaseModel):
    id: int
    original_url: str
    short_code: str
    created_at: datetime
    expires_at: Optional[datetime]
    clicks: int
    last_used_at: Optional[datetime]
    is_active: bool
    user_id: Optional[int]

    class Config:
        from_attributes = True