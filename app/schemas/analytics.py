"""
Pydantic schemas for analytics endpoints
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime


class PostAnalyticsBase(BaseModel):
    """Base schema for post analytics"""
    reactions_like: int = Field(0, ge=0, description="Number of like reactions")
    reactions_praise: int = Field(0, ge=0, description="Number of praise reactions")
    reactions_empathy: int = Field(0, ge=0, description="Number of empathy reactions")
    reactions_interest: int = Field(0, ge=0, description="Number of interest reactions")
    reactions_appreciation: int = Field(0, ge=0, description="Number of appreciation reactions")
    total_impressions: int = Field(0, ge=0, description="Total post impressions")
    total_shares: int = Field(0, ge=0, description="Total number of shares")
    total_comments: int = Field(0, ge=0, description="Total number of comments")


class PostAnalyticsCreate(PostAnalyticsBase):
    """Schema for creating post analytics"""
    pass


class PostAnalyticsUpdate(BaseModel):
    """Schema for updating post analytics (all fields optional)"""
    reactions_like: Optional[int] = Field(None, ge=0)
    reactions_praise: Optional[int] = Field(None, ge=0)
    reactions_empathy: Optional[int] = Field(None, ge=0)
    reactions_interest: Optional[int] = Field(None, ge=0)
    reactions_appreciation: Optional[int] = Field(None, ge=0)
    total_impressions: Optional[int] = Field(None, ge=0)
    total_shares: Optional[int] = Field(None, ge=0)
    total_comments: Optional[int] = Field(None, ge=0)


class PostAnalyticsResponse(PostAnalyticsBase):
    """Schema for post analytics responses"""
    id: int
    post_id: int
    total_reactions: int = Field(description="Calculated total of all reactions")
    total_engagement: int = Field(description="Total engagement (reactions + shares + comments)")
    engagement_rate: float = Field(description="Engagement rate as percentage of impressions")
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PostAnalyticsGraphData(BaseModel):
    """Schema for analytics data formatted for graph visualization"""
    post_id: int
    reactions_breakdown: Dict[str, int] = Field(description="Breakdown of reaction types")
    engagement_metrics: Dict[str, int] = Field(description="Engagement metrics for charts")
    total_engagement: int
    engagement_rate: float
    created_at: datetime
    updated_at: datetime


class TopPostsResponse(BaseModel):
    """Schema for top engaging posts response"""
    post_id: int
    title: str
    content: str = Field(description="Truncated post content")
    author_username: str
    author_full_name: str
    total_engagement: int
    total_reactions: int
    total_impressions: int
    engagement_rate: float


class AnalyticsSummary(BaseModel):
    """Schema for analytics summary"""
    period_days: int = Field(description="Period in days for the summary")
    total_posts: int = Field(description="Total posts with analytics in the period")
    total_impressions: int
    total_reactions: int
    total_shares: int
    total_comments: int
    total_engagement: int = Field(description="Sum of reactions, shares, and comments")
    average_engagement_rate: float = Field(description="Average engagement rate across all posts")


class ReactionUpdate(BaseModel):
    """Schema for updating specific reaction types"""
    reaction_type: str = Field(
        description="Type of reaction", 
        pattern="^(like|praise|empathy|interest|appreciation)$"
    )
    increment: int = Field(1, ge=1, description="Number to increment the reaction by")


class BulkAnalyticsUpdate(BaseModel):
    """Schema for bulk analytics updates"""
    post_ids: list[int] = Field(description="List of post IDs to update")
    analytics_update: PostAnalyticsUpdate = Field(description="Analytics data to apply to all posts")