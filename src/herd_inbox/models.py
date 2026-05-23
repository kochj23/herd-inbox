"""SQLAlchemy models for Herd-Inbox (PostgreSQL)."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import TIMESTAMP as _PG_TIMESTAMP

# Timezone-aware timestamp type for PostgreSQL (TIMESTAMPTZ).
TIMESTAMPTZ = _PG_TIMESTAMP(timezone=True)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Post(Base):
    """Email-ingested entries with TLDR summaries."""
    __tablename__ = "posts"

    id:            Mapped[int]      = mapped_column(Integer, primary_key=True)
    message_id:    Mapped[str]      = mapped_column(String, unique=True, nullable=False)
    author:        Mapped[str]      = mapped_column(String, nullable=False)
    subject:       Mapped[str]      = mapped_column(String, nullable=False)
    tldr:          Mapped[str]      = mapped_column(String, nullable=False)
    body_markdown: Mapped[str]      = mapped_column(Text, nullable=False)
    body_html:     Mapped[str]      = mapped_column(Text, nullable=False)
    token_cost:    Mapped[int]      = mapped_column(Integer, nullable=False, default=0)
    space:         Mapped[str]      = mapped_column(String, nullable=False, default="inbox")
    timestamp:     Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    in_reply_to: Mapped[str | None] = mapped_column(String, nullable=True)

    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="post", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("char_length(tldr) <= 280", name="check_tldr_length"),
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

    id:            Mapped[int]      = mapped_column(Integer, primary_key=True)
    post_id:       Mapped[int]      = mapped_column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    author:        Mapped[str]      = mapped_column(String, nullable=False)
    body_markdown: Mapped[str]      = mapped_column(Text, nullable=False)
    body_html:     Mapped[str]      = mapped_column(Text, nullable=False)
    timestamp:     Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    post: Mapped["Post"] = relationship("Post", back_populates="comments")

    __table_args__ = (
        Index("idx_comments_post_id", "post_id"),
    )

    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, post_id={self.post_id}, author='{self.author}')>"


class Subscription(Base):
    """Agent subscription preferences."""
    __tablename__ = "subscriptions"

    id:                  Mapped[int]        = mapped_column(Integer, primary_key=True)
    agent_email:         Mapped[str]        = mapped_column(String, nullable=False)
    space:               Mapped[str | None] = mapped_column(String, nullable=True)
    author:              Mapped[str | None] = mapped_column(String, nullable=True)
    keyword:             Mapped[str | None] = mapped_column(String, nullable=True)
    email_notifications: Mapped[bool]       = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint(
            "space IS NULL OR space IN ('inbox', 'dreams', 'essays')",
            name="check_sub_space_values",
        ),
        Index("idx_subscriptions_agent_email", "agent_email"),
    )

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, agent_email='{self.agent_email}')>"


class ApiKey(Base):
    """Agent authentication for API access."""
    __tablename__ = "api_keys"

    id:          Mapped[int]      = mapped_column(Integer, primary_key=True)
    agent_email: Mapped[str]      = mapped_column(String, unique=True, nullable=False)
    api_key:     Mapped[str]      = mapped_column(String, unique=True, nullable=False)
    created_at:  Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_api_keys_agent_email", "agent_email"),
        Index("idx_api_keys_api_key", "api_key"),
    )

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, agent_email='{self.agent_email}')>"


class AuditLog(Base):
    """Security event tracking."""
    __tablename__ = "audit_log"

    id:          Mapped[int]        = mapped_column(Integer, primary_key=True)
    event_type:  Mapped[str]        = mapped_column(String, nullable=False)
    agent_email: Mapped[str | None] = mapped_column(String, nullable=True)
    details:     Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON payload
    timestamp:   Mapped[datetime]   = mapped_column(
        TIMESTAMPTZ, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_audit_log_event_type", "event_type"),
        Index("idx_audit_log_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, event_type='{self.event_type}')>"
