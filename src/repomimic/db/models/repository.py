import uuid

from sqlalchemy.orm import (
    Mapped, 
    mapped_column, 
    relationship,
)
from sqlalchemy import (
    String, 
    UniqueConstraint, 
    PrimaryKeyConstraint, 
    CheckConstraint, 
    Uuid,
    Date,
)

from datetime import datetime, date

from .aware_datetime import AwareDateTime
from .base import Base

class Repository(Base):
    """
    Represents a Git repository being indexed.
    
    Columns:
    - id (PK): Unique internal ID.
    - url: Full Git URL (https://github.com/owner/repo.git).
    - owner: Repository owner.
    - name: Repository name.
    - default_branch: Default branch to index (main, master, etc..).
    - last_indexed_commit_sha: Last indexed commit's SHA.
    - last_indexed_at: Timestamp of last indexing run.
    - created_at: Date of when the Repository was created on Github.
    """

    __tablename__ = "repositories"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True), 
        primary_key=True,
        default=uuid.uuid4,
    )
    url: Mapped[str] = mapped_column(
        String(500), 
        nullable=False, 
        unique=True,
    )
    owner: Mapped[str] =  mapped_column(
        String(255), 
        nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
    )
    default_branch: Mapped[str] = mapped_column(
        String(100), 
        nullable=False,
        default="main",
    )
    last_indexed_commit_sha: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )
    last_indexed_at: Mapped[datetime | None] = mapped_column(
        AwareDateTime,
        nullable=True,
    )
    created_at: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    commits = relationship(
        "Commit", 
        back_populates="repository", 
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        PrimaryKeyConstraint("id", name="repositories_pkey"),
        UniqueConstraint("url", name="uq_repositories_url"),
        CheckConstraint(
            url.regexp_match('^https?://(www\\.)?github\\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$', flags='i'),
            name="ck_github_repo_url"
        ),
    )