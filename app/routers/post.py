# routers/posts.py - FIXED VERSION
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel
from database import get_db
from models import Post, PostStatus, User
from utils.auth import CurrentUser, CurrentAdmin
from schemas.post import PostCreate, PostUpdate, PostResponse, PostListResponse
from utils.scheduler_service import schedule_post, unschedule_post, get_scheduled_posts_count, manual_process_now

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Create a new post with proper scheduling integration"""
    db_post = Post(
        title=post_data.title,
        content=post_data.content,
        author_id=current_user.id,
        status=post_data.status or PostStatus.DRAFT
    )
    
    # Handle scheduling 
    if post_data.scheduled_for:
        if post_data.scheduled_for <= datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot schedule post in the past"
            )
        
        # First save the post as draft
        db_post.status = PostStatus.DRAFT
        db.add(db_post)
        db.commit()
        db.refresh(db_post)
        
        # Then schedule it using the service
        schedule_result = schedule_post(
            db=db,
            post_id=db_post.id,
            date=post_data.scheduled_for.strftime('%Y-%m-%d'),
            hour=post_data.scheduled_for.hour,
            minute=post_data.scheduled_for.minute
        )
        
        if not schedule_result["success"]:
            # If scheduling fails, delete the post and raise error
            db.delete(db_post)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=schedule_result["message"]
            )
        
        # Refresh to get the updated scheduled post
        db.refresh(db_post)
    else:
        # Normal post creation (draft/published)
        db.add(db_post)
        db.commit()
        db.refresh(db_post)
    
    return db_post


@router.get("/", response_model=List[PostResponse])
async def get_posts(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    # Filtering parameters
    user_id: Optional[int] = Query(None, description="Filter by author ID"),
    post_status: Optional[PostStatus] = Query(None, description="Filter by post status"),
    start_date: Optional[datetime] = Query(None, description="Filter posts created after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter posts created before this date"),
    # Special scheduled filters
    upcoming_only: Optional[bool] = Query(None, description="For scheduled posts: show only upcoming (not overdue)"),
    # Pagination
    skip: int = Query(0, ge=0, description="Number of posts to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of posts to return")
):
    """
    Get posts with filtering options - unified endpoint for all post queries
    """
    query = db.query(Post)
    
    # Role-based access: Users can only see their own posts, Admins see all
    if current_user.role.value != "admin":
        query = query.filter(Post.author_id == current_user.id)
    
    # Apply filters
    if user_id:
        # Only admins can filter by other users
        if current_user.role.value != "admin" and user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view other users' posts"
            )
        query = query.filter(Post.author_id == user_id)
    
    if post_status:
        query = query.filter(Post.status == post_status)
        
        # Special handling for scheduled posts
        if post_status == PostStatus.SCHEDULED and upcoming_only is not None:
            if upcoming_only:
                query = query.filter(Post.scheduled_for > datetime.utcnow())
            else:
                query = query.filter(Post.scheduled_for <= datetime.utcnow())

    if start_date:
        query = query.filter(Post.created_at >= start_date)
    
    if end_date:
        query = query.filter(Post.created_at <= end_date)
    
    # Order scheduled posts by scheduled_for, others by created_at
    if post_status == PostStatus.SCHEDULED:
        query = query.order_by(Post.scheduled_for.asc())
    else:
        query = query.order_by(Post.created_at.desc())
    
    # Execute query with pagination
    posts = query.offset(skip).limit(limit).all()
    return posts


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Get a specific post by ID"""
    post = db.query(Post).filter(Post.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check authorization
    if current_user.role.value != "admin" and post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this post"
        )
    
    return post


@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    post_data: PostUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Update a post with proper scheduling integration"""
    post = db.query(Post).filter(Post.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check authorization
    if current_user.role.value != "admin" and post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post"
        )
    
    # Get update data
    update_data = post_data.dict(exclude_unset=True)
    
    # Handle scheduling changes
    if "scheduled_for" in update_data:
        new_schedule_time = update_data["scheduled_for"]
        
        if new_schedule_time:
            # User wants to schedule/reschedule
            if new_schedule_time <= datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot schedule post in the past"
                )
            
            # Use scheduler service to handle the scheduling
            schedule_result = schedule_post(
                db=db,
                post_id=post_id,
                date=new_schedule_time.strftime('%Y-%m-%d'),
                hour=new_schedule_time.hour,
                minute=new_schedule_time.minute
            )
            
            if not schedule_result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=schedule_result["message"]
                )
            
            # Remove scheduled_for from update_data since it's handled by scheduler service
            del update_data["scheduled_for"]
            # Also remove status if it was set, since scheduler service handles it
            if "status" in update_data:
                del update_data["status"]
                
        else:
            # User wants to unschedule (set scheduled_for to None)
            if post.status == PostStatus.SCHEDULED:
                unschedule_result = unschedule_post(db=db, post_id=post_id)
                if not unschedule_result["success"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=unschedule_result["message"]
                    )
            
            # Remove from update_data since it's handled
            del update_data["scheduled_for"]
    
    # Apply remaining updates
    for field, value in update_data.items():
        setattr(post, field, value)
    
    db.commit()
    db.refresh(post)
    
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """Delete a post"""
    post = db.query(Post).filter(Post.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check authorization
    if current_user.role.value != "admin" and post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post"
        )
    
    db.delete(post)
    db.commit()


# SCHEDULING ENDPOINTS

class ScheduleRequest(BaseModel):
    date: str  # YYYY-MM-DD format
    hour: int  # 0-23
    minute: int  # 0-59

class ScheduleResponse(BaseModel):
    success: bool
    message: str

@router.post("/{post_id}/schedule", response_model=ScheduleResponse)
async def schedule_post_endpoint(
    post_id: int,
    schedule_data: ScheduleRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Schedule a post for specific date, hour, and minute
    Example: POST /posts/1/schedule
    Body: {"date": "2025-01-20", "hour": 14, "minute": 30}
    """
    # Check if user owns the post (or is admin)
    post = db.query(Post).filter(Post.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    if current_user.role.value != "admin" and post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to schedule this post"
        )
    
    # Call the scheduling service
    result = schedule_post(
        db=db, 
        post_id=post_id, 
        date=schedule_data.date, 
        hour=schedule_data.hour, 
        minute=schedule_data.minute
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return ScheduleResponse(
        success=True,
        message=result["message"]
    )

@router.post("/{post_id}/unschedule", response_model=ScheduleResponse)
async def unschedule_post_endpoint(
    post_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Unschedule a post (revert to draft)
    Example: POST /posts/1/unschedule
    """
    # Check if user owns the post (or is admin)
    post = db.query(Post).filter(Post.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    if current_user.role.value != "admin" and post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this post"
        )
    
    # Call the unscheduling service
    result = unschedule_post(db=db, post_id=post_id)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return ScheduleResponse(
        success=True,
        message=result["message"]
    )


# ADMIN ENDPOINTS

@router.get("/user/{user_id}", response_model=List[PostResponse])
async def get_user_posts(
    user_id: int,
    current_admin: CurrentAdmin,  # Only admins can access this endpoint
    db: Session = Depends(get_db),
    post_status: Optional[PostStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Admin-only: Get all posts by a specific user"""
    query = db.query(Post).filter(Post.author_id == user_id)

    if post_status:
        query = query.filter(Post.status == post_status)

    posts = query.offset(skip).limit(limit).all()
    return posts

@router.get("/admin/scheduler-stats")
async def get_scheduler_stats(
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    """
    Admin only: Get scheduler statistics
    Example: GET /posts/admin/scheduler-stats
    """
    stats = get_scheduled_posts_count(db)
    return {
        "timestamp": datetime.utcnow(),
        "stats": stats
    }

@router.post("/admin/process-now")
async def process_scheduled_now(
    current_admin: CurrentAdmin,
):
    """
    Admin only: Manually trigger processing of due posts
    Example: POST /posts/admin/process-now
    """
    result = await manual_process_now()
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to process posts")
        )
    
    return {
        "message": f"Successfully processed {result['processed_count']} posts",
        "processed_count": result["processed_count"]
    }

@router.get("/admin/overdue")
async def get_overdue_posts(
    current_admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    """
    Admin only: Get all overdue scheduled posts
    Example: GET /posts/admin/overdue
    """
    overdue_posts = db.query(Post).filter(
        Post.status == PostStatus.SCHEDULED,
        Post.scheduled_for <= datetime.utcnow()
    ).order_by(Post.scheduled_for.asc()).all()
    
    return {
        "count": len(overdue_posts),
        "posts": overdue_posts
    }

