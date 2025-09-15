from sqlalchemy import Column, Integer, BigInteger, DateTime, ForeignKey,Index, func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func as sql_func
from database import Base


class PostAnalytics(Base):
    """
    Analytics model for tracking post engagement metrics
    """
    __tablename__ = "post_analytics"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, unique=True)

    # LinkedIn reaction types as specified in requirements
    reactions_like = Column(BigInteger, default=0, nullable=False)
    reactions_praise = Column(BigInteger, default=0, nullable=False)
    reactions_empathy = Column(BigInteger, default=0, nullable=False)
    reactions_interest = Column(BigInteger, default=0, nullable=False)
    reactions_appreciation = Column(BigInteger, default=0, nullable=False)

    # Engagement metrics
    total_impressions = Column(BigInteger, default=0, nullable=False)
    total_shares = Column(BigInteger, default=0, nullable=False)
    total_comments = Column(BigInteger, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=sql_func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=sql_func.now(), onupdate=sql_func.now(), nullable=False)

    # Relationships
    post = relationship("Post", back_populates="analytics")

    @hybrid_property
    def total_reactions(self):
        """Calculate total reactions across all types"""
        return (
            self.reactions_like + 
            self.reactions_praise + 
            self.reactions_empathy + 
            self.reactions_interest + 
            self.reactions_appreciation
        )

    @total_reactions.expression
    def total_reactions(cls):
        """SQLAlchemy expression for total_reactions in queries"""
        return (
            cls.reactions_like + 
            cls.reactions_praise + 
            cls.reactions_empathy + 
            cls.reactions_interest + 
            cls.reactions_appreciation
        )

    @hybrid_property
    def total_engagement(self):
        """
        Calculate total engagement (reactions + shares + comments)
        """
        return self.total_reactions + self.total_shares + self.total_comments

    @total_engagement.expression
    def total_engagement(cls):
        """SQLAlchemy expression for total_engagement in queries"""
        return (
            cls.reactions_like + 
            cls.reactions_praise + 
            cls.reactions_empathy + 
            cls.reactions_interest + 
            cls.reactions_appreciation +
            cls.total_shares + 
            cls.total_comments
        )

    @hybrid_property
    def engagement_rate(self):
        """Calculate engagement rate as percentage of impressions"""
        if self.total_impressions == 0:
            return 0.0
        return (self.total_engagement / self.total_impressions) * 100

    @engagement_rate.expression
    def engagement_rate(cls):
        """SQLAlchemy expression for engagement_rate in queries"""
        return func.case(
            (cls.total_impressions == 0, 0.0),
            else_=(
                (cls.reactions_like + cls.reactions_praise + cls.reactions_empathy + 
                 cls.reactions_interest + cls.reactions_appreciation + 
                 cls.total_shares + cls.total_comments).cast(Float) / 
                cls.total_impressions.cast(Float) * 100
            )
        )

    def __repr__(self):
        return f"<PostAnalytics(post_id={self.post_id}, total_engagement={self.total_engagement})>"


# Database indexes for performance optimization
Index("idx_analytics_post_id", PostAnalytics.post_id)
Index("idx_analytics_created_at", PostAnalytics.created_at)
Index("idx_analytics_total_engagement", PostAnalytics.total_impressions, PostAnalytics.total_shares, PostAnalytics.total_comments)