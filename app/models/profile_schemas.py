"""User profile schemas"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class ProfileResponse(BaseModel):
    email: EmailStr
    name: str
    role: str
    bio: Optional[str] = None
    organization: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[HttpUrl] = None
    location: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    email_verified: bool
    active: bool
    created_at: datetime
    updated_at: datetime


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2)
    bio: Optional[str] = Field(None, max_length=500)
    organization: Optional[str] = Field(None, max_length=200)
    position: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[HttpUrl] = None
    location: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[HttpUrl] = None


class ProfileStats(BaseModel):
    total_submissions: int = 0
    completed_reviews: int = 0
    pending_reviews: int = 0
    account_age_days: int = 0
