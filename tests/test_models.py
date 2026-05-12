"""Tests for SQLAlchemy models (PostgreSQL)."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from herd_inbox.models import ApiKey, AuditLog, Base, Comment, Post, Subscription


class TestPostModel:
    def test_create_post(self, db_session: Session):
        post = Post(
            message_id="msg-model-001",
            author="test@example.com",
            subject="Model Test",
            tldr="Short summary",
            body_markdown="# Hello",
            body_html="<h1>Hello</h1>",
            token_cost=42,
            space="inbox",
        )
        db_session.add(post)
        db_session.flush()

        result = db_session.query(Post).filter_by(message_id="msg-model-001").first()
        assert result is not None
        assert result.author == "test@example.com"
        assert result.space == "inbox"
        assert result.token_cost == 42

    def test_post_default_space(self, db_session: Session):
        post = Post(
            message_id="msg-default-space",
            author="test@example.com",
            subject="Default Space",
            tldr="Summary",
            body_markdown="Body",
            body_html="<p>Body</p>",
        )
        db_session.add(post)
        db_session.flush()

        result = db_session.query(Post).filter_by(message_id="msg-default-space").first()
        assert result.space == "inbox"

    def test_post_comments_relationship(self, db_session: Session):
        post = Post(
            message_id="msg-rel-test",
            author="test@example.com",
            subject="Relationship Test",
            tldr="Summary",
            body_markdown="Body",
            body_html="<p>Body</p>",
        )
        db_session.add(post)
        db_session.flush()

        comment = Comment(
            post_id=post.id,
            author="commenter@example.com",
            body_markdown="Nice!",
            body_html="<p>Nice!</p>",
        )
        db_session.add(comment)
        db_session.flush()

        db_session.refresh(post)
        assert len(post.comments) == 1
        assert post.comments[0].author == "commenter@example.com"

    def test_post_repr(self, db_session: Session):
        post = Post(
            message_id="msg-repr",
            author="test@example.com",
            subject="Repr Test",
            tldr="Summary",
            body_markdown="Body",
            body_html="<p>Body</p>",
        )
        db_session.add(post)
        db_session.flush()
        assert "Post" in repr(post)
        assert "test@example.com" in repr(post)

    def test_timestamp_auto_populated(self, db_session: Session):
        post = Post(
            message_id="msg-ts",
            author="test@example.com",
            subject="Timestamp",
            tldr="Summary",
            body_markdown="Body",
            body_html="<p>Body</p>",
        )
        db_session.add(post)
        db_session.flush()
        assert post.timestamp is not None
        assert isinstance(post.timestamp, datetime)


class TestCommentModel:
    def _make_post(self, db_session: Session, mid: str = "msg-for-comment") -> Post:
        post = Post(
            message_id=mid,
            author="author@example.com",
            subject="Has Comments",
            tldr="Summary",
            body_markdown="Body",
            body_html="<p>Body</p>",
        )
        db_session.add(post)
        db_session.flush()
        return post

    def test_create_comment(self, db_session: Session):
        post = self._make_post(db_session)
        comment = Comment(
            post_id=post.id,
            author="commenter@example.com",
            body_markdown="Reply text",
            body_html="<p>Reply text</p>",
        )
        db_session.add(comment)
        db_session.flush()

        result = db_session.query(Comment).filter_by(post_id=post.id).first()
        assert result is not None
        assert result.author == "commenter@example.com"

    def test_comment_post_backref(self, db_session: Session):
        post = self._make_post(db_session, "msg-backref")
        comment = Comment(
            post_id=post.id,
            author="commenter@example.com",
            body_markdown="Reply",
            body_html="<p>Reply</p>",
        )
        db_session.add(comment)
        db_session.flush()
        db_session.refresh(comment)
        assert comment.post.id == post.id

    def test_cascade_delete(self, db_session: Session):
        post = self._make_post(db_session, "msg-cascade")
        comment = Comment(
            post_id=post.id,
            author="c@d.com",
            body_markdown="Goes away",
            body_html="<p>Goes away</p>",
        )
        db_session.add(comment)
        db_session.flush()
        db_session.delete(post)
        db_session.flush()
        assert db_session.query(Comment).filter_by(post_id=post.id).count() == 0


class TestSubscriptionModel:
    def test_create_subscription(self, db_session: Session):
        sub = Subscription(agent_email="agent@example.com", space="inbox", email_notifications=True)
        db_session.add(sub)
        db_session.flush()

        result = db_session.query(Subscription).filter_by(agent_email="agent@example.com").first()
        assert result.space == "inbox"
        assert result.email_notifications is True

    def test_subscription_nullable_fields(self, db_session: Session):
        sub = Subscription(agent_email="minimal@example.com")
        db_session.add(sub)
        db_session.flush()

        result = db_session.query(Subscription).filter_by(agent_email="minimal@example.com").first()
        assert result.space is None
        assert result.author is None
        assert result.keyword is None


class TestApiKeyModel:
    def test_create_api_key(self, db_session: Session):
        key = ApiKey(agent_email="agent@example.com", api_key="herd_testkey123")
        db_session.add(key)
        db_session.flush()

        result = db_session.query(ApiKey).filter_by(agent_email="agent@example.com").first()
        assert result.api_key == "herd_testkey123"

    def test_created_at_auto_populated(self, db_session: Session):
        key = ApiKey(agent_email="dated@example.com", api_key="herd_datedkey")
        db_session.add(key)
        db_session.flush()

        result = db_session.query(ApiKey).filter_by(agent_email="dated@example.com").first()
        assert result.created_at is not None
        assert isinstance(result.created_at, datetime)

    def test_duplicate_agent_email_raises(self, db_session: Session):
        db_session.add(ApiKey(agent_email="dup@example.com", api_key="herd_key1"))
        db_session.flush()
        with pytest.raises(IntegrityError):
            db_session.add(ApiKey(agent_email="dup@example.com", api_key="herd_key2"))
            db_session.flush()


class TestAuditLogModel:
    def test_create_audit_entry(self, db_session: Session):
        entry = AuditLog(
            event_type="injection_attempt",
            agent_email="bad@example.com",
            details='{"payload": "<script>alert(1)</script>"}',
        )
        db_session.add(entry)
        db_session.flush()

        result = db_session.query(AuditLog).filter_by(event_type="injection_attempt").first()
        assert result.agent_email == "bad@example.com"

    def test_nullable_agent_email(self, db_session: Session):
        entry = AuditLog(event_type="rate_limit", details='{"ip": "1.2.3.4"}')
        db_session.add(entry)
        db_session.flush()

        result = db_session.query(AuditLog).filter_by(event_type="rate_limit").first()
        assert result.agent_email is None


class TestSchemaIntrospection:
    """Verify that SQLAlchemy models declare the expected columns."""

    def test_all_tables_in_metadata(self, pg_engine):
        inspector = inspect(pg_engine)
        tables = set(inspector.get_table_names())
        assert {"posts", "comments", "subscriptions", "api_keys", "audit_log"}.issubset(tables)

    def test_posts_columns(self, pg_engine):
        inspector = inspect(pg_engine)
        columns = {c["name"] for c in inspector.get_columns("posts")}
        assert {
            "id", "message_id", "author", "subject", "tldr",
            "body_markdown", "body_html", "token_cost", "space",
            "timestamp", "in_reply_to",
        }.issubset(columns)

    def test_timestamptz_on_posts(self, pg_engine):
        inspector = inspect(pg_engine)
        ts_col = next(c for c in inspector.get_columns("posts") if c["name"] == "timestamp")
        # PostgreSQL TIMESTAMPTZ renders as TIMESTAMP WITH TIME ZONE in SQLAlchemy
        assert "TIMESTAMP" in str(ts_col["type"]).upper()
