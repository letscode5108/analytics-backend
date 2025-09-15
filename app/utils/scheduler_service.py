
import asyncio
import logging
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import and_


from database import SessionLocal 
from models import Post, PostStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LinkedInAPISimulator:
    """Simple LinkedIn API simulator"""
    
    @staticmethod
    async def publish_post(post_id: int, title: str, content: str) -> bool:
        """Simulate publishing to LinkedIn"""
        await asyncio.sleep(0.2)  # Simulate API delay
    
    
        import random
        success = random.random() < 0.95
        
        if success:
            logger.info(f" Published post {post_id} to LinkedIn successfully")
            return True
        else:
            logger.error(f" Failed to publish post {post_id} to LinkedIn")
            return False

class PostSchedulerService:
    """Simple post scheduler service"""
    
    def __init__(self):
        self.linkedin_api = LinkedInAPISimulator()
        self.running = False
    
    async def process_due_posts(self) -> int:
        """Process all posts that are due for publishing"""
        # Create a new database session specifically for the scheduler
        db = SessionLocal()
        
        try:
            # Find all scheduled posts that are due
            current_time = datetime.utcnow()
            due_posts = db.query(Post).filter(
                and_(
                    Post.status == PostStatus.SCHEDULED,
                    Post.scheduled_for <= current_time
                )
            ).all()
            
            if not due_posts:
                logger.info("No due posts found")
                return 0
            
            logger.info(f" Processing {len(due_posts)} due posts...")
            
            processed = 0
            for post in due_posts:
                try:
                    # Call LinkedIn API simulator
                    success = await self.linkedin_api.publish_post(
                        post.id, post.title, post.content
                    )
                    
                    if success:
                        # Update post status to published
                        post.status = PostStatus.PUBLISHED
                        post.published_at = datetime.utcnow()
                        post.linkedin_post_id = f"linkedin_{post.id}_{int(datetime.utcnow().timestamp())}"
                        logger.info(f" Post {post.id} published successfully")
                    else:
                        # Handle failure
                        post.error_message = "Failed to publish to LinkedIn"
                        logger.error(f"Post {post.id} failed to publish")
                    
                    processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing post {post.id}: {str(e)}")
                    post.error_message = str(e)
            
            # Commit all changes at once
            db.commit()
            logger.info(f"Processed {processed} posts")
            return processed
            
        except Exception as e:
            logger.error(f" Error in process_due_posts: {str(e)}")
            db.rollback()
            return 0
        finally:
            # Properly close the database session
            db.close()
    
    async def run_scheduler(self, interval_seconds: int = 30):
        """Run the scheduler continuously"""
        self.running = True
        logger.info(f" Scheduler started (checking every {interval_seconds}s)")
        
        while self.running:
            try:
                processed = await self.process_due_posts()
                if processed > 0:
                    logger.info(f"📊 Batch complete: {processed} posts processed")
                else:
                    # Only log this every 5 minutes to avoid spam
                    import time
                    if not hasattr(self, '_last_no_posts_log'):
                        self._last_no_posts_log = 0
                    
                    current_time = time.time()
                    if current_time - self._last_no_posts_log > 300:  # 5 minutes
                        logger.info("📭 No posts to process")
                        self._last_no_posts_log = current_time
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f" Scheduler error: {str(e)}")
                await asyncio.sleep(interval_seconds)
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("⏹️ Scheduler stopped")

# Global scheduler instance
scheduler = PostSchedulerService()

def validate_schedule_time(scheduled_for: datetime) -> bool:
    """Validate that scheduled time is in the future"""
    return scheduled_for > datetime.utcnow()

def schedule_post(db: Session, post_id: int, date: str, hour: int, minute: int) -> dict:
    """
    Schedule a post for a specific date/time
    """
    try:
        # Get the post
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            return {"success": False, "message": "Post not found"}
        
        # Check if post can be scheduled
        if post.status not in [PostStatus.DRAFT, PostStatus.SCHEDULED]:
            return {"success": False, "message": f"Cannot schedule post with status: {post.status.value}"}
        
        # Parse and validate datetime
        try:
            scheduled_datetime = datetime.strptime(date, '%Y-%m-%d')
            scheduled_datetime = scheduled_datetime.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except ValueError:
            return {"success": False, "message": "Invalid date format. Use YYYY-MM-DD"}
        
        # Validate hour and minute
        if not (0 <= hour <= 23):
            return {"success": False, "message": "Hour must be between 0-23"}
        if not (0 <= minute <= 59):
            return {"success": False, "message": "Minute must be between 0-59"}
        
        # Check if time is in the future
        if not validate_schedule_time(scheduled_datetime):
            return {"success": False, "message": "Cannot schedule post in the past"}
      
      
        post.scheduled_for = scheduled_datetime
        post.status = PostStatus.SCHEDULED
        post.error_message = None  
        
        db.commit()
        db.refresh(post)
        
        return {
            "success": True, 
            "message": f"Post scheduled for {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}",
            "post": post
        }
        
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Error scheduling post: {str(e)}"}

def unschedule_post(db: Session, post_id: int) -> dict:
    """Unschedule a post (revert to draft)"""
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            return {"success": False, "message": "Post not found"}
        
        if post.status != PostStatus.SCHEDULED:
            return {"success": False, "message": "Post is not scheduled"}
        
        post.status = PostStatus.DRAFT
        post.scheduled_for = None
        
        db.commit()
        db.refresh(post)
        
        return {"success": True, "message": "Post unscheduled successfully", "post": post}
        
    except Exception as e:
        db.rollback()
        return {"success": False, "message": f"Error unscheduling post: {str(e)}"}

def get_scheduled_posts_count(db: Session) -> dict:
    """Get count of scheduled posts"""
    try:
        current_time = datetime.utcnow()
        
        # Total scheduled posts
        total_scheduled = db.query(Post).filter(Post.status == PostStatus.SCHEDULED).count()
        
        # Overdue posts
        overdue = db.query(Post).filter(
            and_(
                Post.status == PostStatus.SCHEDULED,
                Post.scheduled_for <= current_time
            )
        ).count()
        
        # Upcoming posts (next 24 hours)
        from datetime import timedelta
        tomorrow = current_time + timedelta(days=1)
        upcoming = db.query(Post).filter(
            and_(
                Post.status == PostStatus.SCHEDULED,
                Post.scheduled_for > current_time,
                Post.scheduled_for <= tomorrow
            )
        ).count()
        
        return {
            "total_scheduled": total_scheduled,
            "overdue": overdue,
            "upcoming_24h": upcoming
        }
        
    except Exception as e:
        return {"error": str(e)}

async def manual_process_now() -> dict:
    """Manually trigger post processing"""
    try:
        processed = await scheduler.process_due_posts()
        return {"success": True, "processed_count": processed}
    except Exception as e:
        return {"success": False, "error": str(e)}