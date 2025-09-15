# Import all models to ensure they're registered with SQLAlchemy
from .user import User, UserRole
from .post import Post, PostStatus
from .analytics import PostAnalytics

# Make models available for import
__all__ = [
    "User",
    "UserRole", 
    "Post",
    "PostStatus",
    "PostAnalytics"
]