# schemas/posts.py
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, validator, Field
from enum import Enum

from models import PostStatus


class PostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500, description="Post title")
    content: str = Field(..., min_length=1, description="Post content")


class PostCreate(PostBase):
    status: Optional[PostStatus] = None
    scheduled_for: Optional[datetime] = None
    
    @validator('scheduled_for')
    def validate_scheduled_for(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('Cannot schedule post in the past')
        return v


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    status: Optional[PostStatus] = None
    scheduled_for: Optional[datetime] = None
    
    @validator('scheduled_for')
    def validate_scheduled_for(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('Cannot schedule post in the past')
        return v


class PostResponse(PostBase):
    id: int
    status: PostStatus
    author_id: int
    scheduled_for: Optional[datetime]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    linkedin_post_id: Optional[str]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class PostListResponse(BaseModel):
    posts: List[PostResponse]
    total: int
    skip: int
    limit: int


class PostWithAuthor(PostResponse):
    """Extended post response with author information"""
    author: dict  # Will contain author info when needed
    
    class Config:
        from_attributes = True