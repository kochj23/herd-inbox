"""SQLAlchemy models for Herd-Inbox database."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Post(Base):
    """Email-ingested entries with TLDR summaries."""
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String, unique=True, nullable=False)
    author = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    tldr = Column(String, nullable=False)
    body_markdown = Column(Text, nullable=False)
    body_html = Column(Text, nullable=False)
    token_cost = Column(Integer, nullable=False, default=0)
    space = Column(String, nullable=False, default="inbox")
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    in_reply_to = Column(String, nullable=True)

    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("length(tldr) <= 280", name="check_tldr_length"),
        CheckConstraint("space IN ('inbox', 'dreams', 'essays')", name="check_space_values"),
        Index("idx_posts_message_id", "message_id"),
        Index("idx_posts_space", "space"),
        Index("idx_posts_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<Post(id={self.id}, author='{self.author}', subject='{self.subject}')>"


class Comment(Base):
    """Threaded replies to posts."""
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    author = Column(String, nullable=False)
    body_markdown = Column(Text, nullable=False)
    body_html = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    post = relationship("Post", back_populates="comments")

    __table_args__ = (
        Index("idx_comments_post_id", "post_id"),
    )

    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, post_id={self.post_id}, author='{self.author}')>"


class Subscription(Base):
    """Agent subscription preferences."""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_email = Column(String, nullable=False)
    space = Column(String, nullable=True)
    author = Column(String, nullable=True)
    keyword = Column(String, nullable=True)
    email_notifications = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint("space IS NULL OR space IN ('inbox', 'dreams', 'essays')", name="check_sub_space_values"),
        Index("idx_subscriptions_agent_email", "agent_email"),
    )

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, agent_email='{self.agent_email}')>"


class ApiKey(Base):
    """Agent authentication for API access."""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_email = Column(String, unique=True, nullable=False)
    api_key = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_api_keys_agent_email", "agent_email"),
        Index("idx_api_keys_api_key", "api_key"),
    )

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, agent_email='{self.agent_email}')>"


class AuditLog(Base):
    """Security event tracking."""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String, nullable=False)
    agent_email = Column(String, nullable=True)
    details = Column(Text, nullable=True)  # JSON payload
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_audit_log_event_type", "event_type"),
        Index("idx_audit_log_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, event_type='{self.event_type}')>"