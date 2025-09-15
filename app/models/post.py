from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database import Base


class PostStatus(str, enum.Enum):
    """Post status for managing post lifecycle"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"  # For failed scheduled posts


class Post(Base):
    """
    Post model for managing user posts and scheduling
    """
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(Enum(PostStatus), default=PostStatus.DRAFT, nullable=False)
    
    # Author relationship
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Scheduling fields
    scheduled_for = Column(DateTime(timezone=True), nullable=True)  # When to publish
    published_at = Column(DateTime(timezone=True), nullable=True)   # When actually published
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Additional fields for LinkedIn simulation
    linkedin_post_id = Column(String, nullable=True)  # Simulated LinkedIn post ID
    error_message = Column(Text, nullable=True)       # Error message if publishing failed

    # Relationships
    author = relationship("User", back_populates="posts")
    analytics = relationship("PostAnalytics", back_populates="post", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title[:30]}...', status='{self.status}')>"


# Database indexes for performance
Index("idx_posts_author_status", Post.author_id, Post.status)
Index("idx_posts_scheduled_for", Post.scheduled_for)
Index("idx_posts_published_at", Post.published_at)
Index("idx_posts_created_at", Post.created_at)