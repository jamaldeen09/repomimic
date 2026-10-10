import uuid

from sqlalchemy.orm import (
    Mapped, 
    mapped_column, 
    relationship,
)
from sqlalchemy import (
    String, 
    func, 
    UniqueConstraint, 
    PrimaryKeyConstraint, 
    ForeignKey, 
    Uuid,
    Index,
    Text,
    Date,
    ForeignKeyConstraint,
)
from datetime import datetime, date

from .aware_datetime import AwareDateTime
from .base import Base

class Commit(Base):
    """
    Represents a Git commit in the repository.
    
    Columns:
    - id (PK): Unique internal ID.
    - repository_id: Unique Identifier for a Repository.
    - commit_sha: Git commit SHA (full 40 chars).
    - commit_message: Commit message text.
    - committed_at: Timestamp of commit.
    - indexed_at: When a commit was processed.
    """
    __tablename__ = "commits"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True), 
        primary_key=True,
        default=uuid.uuid4,
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    commit_sha: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        nullable=False,
    )
    indexed_at: Mapped[datetime] = mapped_column(
        AwareDateTime,
        default=func.now(),
        nullable=False,
    )
    commit_message: Mapped[str] = mapped_column(Text)
    committed_at: Mapped[date] = mapped_column(Date, nullable=False)
    
    repository = relationship("Repository", back_populates="commits")
    blobs = relationship(
        "Blob", 
        back_populates="commit", 
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        PrimaryKeyConstraint("id", name="commits_pkey"),
        ForeignKeyConstraint(
            columns=["repository_id"],
            refcolumns=["repositories.id"],
            name="fk_commits_repository_id",
            ondelete="CASCADE",
        ),
        UniqueConstraint("commit_sha", name="uq_commits_commit_sha"),
        Index("ix_commits_repository_id_committed_at", "repository_id", "committed_at"),
    )


