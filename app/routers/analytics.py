"""
Analytics router for LinkedIn Analytics Backend
Handles post analytics CRUD operations and data aggregation
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_, func, case
from database import get_db
from models import Post, PostAnalytics, User, PostStatus
from schemas.analytics import (
    PostAnalyticsCreate, 
    PostAnalyticsUpdate, 
    PostAnalyticsResponse,
    PostAnalyticsGraphData,
    TopPostsResponse,
    AnalyticsSummary
)
from utils.auth import CurrentUser, CurrentAdmin, get_current_admin_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_post_with_access_check(db: Session, post_id: int, current_user: User) -> Post:
    """Helper to get post and verify user has access"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Admin can access all posts, users only their own
    # Check for different possible field names for the post owner
    post_owner_id = None
    if hasattr(post, 'user_id'):
        post_owner_id = post.user_id
    elif hasattr(post, 'author_id'):
        post_owner_id = post.author_id
    elif hasattr(post, 'created_by'):
        post_owner_id = post.created_by
    elif hasattr(post, 'owner_id'):
        post_owner_id = post.owner_id
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Post model missing owner field"
        )
    
@router.post("/{post_id}", response_model=PostAnalyticsResponse, status_code=status.HTTP_201_CREATED)
def create_post_analytics(
    post_id: int,
    analytics_data: PostAnalyticsCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Create analytics for a post (only if post exists and user has access)"""
    
    # Verify post exists and user has access
    post = get_post_with_access_check(db, post_id, current_user)
    
    # Check if analytics already exist for this post
    existing_analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == post_id).first()
    if existing_analytics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analytics already exist for this post"
        )
    
    # Create new analytics
    db_analytics = PostAnalytics(
        post_id=post_id,
        **analytics_data.model_dump()
    )
    
    db.add(db_analytics)
    db.commit()
    db.refresh(db_analytics)
    
    return db_analytics


@router.get("/{post_id}", response_model=PostAnalyticsResponse)
def get_post_analytics(
    post_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Get analytics for a specific post"""
    
    # Verify post exists and user has access
    get_post_with_access_check(db, post_id, current_user)
    
    analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == post_id).first()
    if not analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics not found for this post"
        )
    
    return analytics


@router.put("/{post_id}", response_model=PostAnalyticsResponse)
def update_post_analytics(
    post_id: int,
    analytics_update: PostAnalyticsUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Update analytics for a post"""
    
    # Verify post exists and user has access
    get_post_with_access_check(db, post_id, current_user)
    
    analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == post_id).first()
    if not analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics not found for this post"
        )
    
    # Update only provided fields
    update_data = analytics_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(analytics, field, value)
    
    db.commit()
    db.refresh(analytics)
    
    return analytics


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post_analytics(
    post_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Delete analytics for a post"""
    
    # Verify post exists and user has access
    get_post_with_access_check(db, post_id, current_user)
    
    analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == post_id).first()
    if not analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics not found for this post"
        )
    
    db.delete(analytics)
    db.commit()


@router.get("/posts/top", response_model=List[TopPostsResponse])
def get_top_engaging_posts(
    current_user: CurrentUser,
    limit: int = Query(5, ge=1, le=50, description="Number of top posts to return"),
    days_back: Optional[int] = Query(None, ge=1, le=365, description="Filter posts from last N days"),
    db: Session = Depends(get_db)
):
    """Get top engaging posts (filtered by user role)"""
    
    query = db.query(
        PostAnalytics,
        Post.title,
        Post.content,
        User.username,
        User.full_name
    ).join(
        Post, PostAnalytics.post_id == Post.id
    ).join(
        User, Post.author_id  == User.id
    )
    
    # Apply time filter if specified
    if days_back:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        query = query.filter(Post.created_at >= cutoff_date)
    
    # Apply role-based filtering
    if current_user.role.value != "admin":
        query = query.filter(Post.author_id == current_user.id)
    
    # Order by total engagement and limit
    results = query.order_by(desc(PostAnalytics.total_engagement)).limit(limit).all()
    
    return [
        TopPostsResponse(
            post_id=analytics.post_id,
            title=title,
            content=content[:200] + "..." if len(content) > 200 else content,
            author_username=username,
            author_full_name=full_name,
            total_engagement=analytics.total_engagement,
            total_reactions=analytics.total_reactions,
            total_impressions=analytics.total_impressions,
            engagement_rate=analytics.engagement_rate
        )
        for analytics, title, content, username, full_name in results
    ]


@router.get("/posts/{post_id}/graph", response_model=PostAnalyticsGraphData)
def get_post_analytics_graph_data(
    post_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Get analytics data formatted for graph visualization"""
    
    # Verify post exists and user has access
    get_post_with_access_check(db, post_id, current_user)
    
    analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == post_id).first()
    if not analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics not found for this post"
        )
    
    # Format data for charts
    reactions_breakdown = {
        "like": analytics.reactions_like,
        "praise": analytics.reactions_praise,
        "empathy": analytics.reactions_empathy,
        "interest": analytics.reactions_interest,
        "appreciation": analytics.reactions_appreciation
    }
    
    engagement_metrics = {
        "reactions": analytics.total_reactions,
        "shares": analytics.total_shares,
        "comments": analytics.total_comments,
        "impressions": analytics.total_impressions
    }
    
    return PostAnalyticsGraphData(
        post_id=post_id,
        reactions_breakdown=reactions_breakdown,
        engagement_metrics=engagement_metrics,
        total_engagement=analytics.total_engagement,
        engagement_rate=analytics.engagement_rate,
        created_at=analytics.created_at,
        updated_at=analytics.updated_at
    )



# Admin-only endpoints for managing all analytics
@router.get("/admin/all", response_model=List[PostAnalyticsResponse])
def get_all_analytics(
    current_admin: CurrentAdmin,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Admin only: Get all post analytics with pagination"""
    
    analytics_list = db.query(PostAnalytics).offset(offset).limit(limit).all()
    return analytics_list


@router.delete("/admin/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_post_analytics(
    post_id: int,
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    """Admin only: Delete analytics for any post"""
    
    analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == post_id).first()
    if not analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics not found for this post"
        )
    
    db.delete(analytics)
    db.commit()