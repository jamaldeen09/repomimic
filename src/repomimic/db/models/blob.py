import uuid

from sqlalchemy.orm import (
    Mapped, 
    mapped_column, 
    relationship,
)
from sqlalchemy import (
    String, 
    func, 
    PrimaryKeyConstraint, 
    ForeignKey, 
    Uuid,
    Index,
    Boolean,
    ForeignKeyConstraint,
    Enum as SQLAlchemyEnum,
    LargeBinary,
)
from datetime import datetime
from .aware_datetime import AwareDateTime
from enum import Enum
from pgvector.sqlalchemy import Vector

from .base import Base

class LanguageEnum(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"

class Blob(Base):
    """
    Represents a source code file at a specific commit.
    
    Columns:
    - id (PK): Unique internal ID.
    - repository_id (FK): Foreign key to Repository.
    - commit_id (FK): Foreign key to Commit (which version of the file).
    - blob_sha: Git blob SHA (identifies unique file content).
    - file_path: Relative path in repo (e.g., src/auth.py).
    - file_name: Just the filename (auth.py).
    - language: Programming language detected from extension.
    - content_bytes: Bytes of the source code to avoid storing large content in the db.
    - embedding: Vector embedding for similarity search (pgvector).
    - created_at: When the blob was created.
    - is_deleted: True if file was removed in later commits.
    """
    __tablename__ = "blobs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True), 
        primary_key=True,
        default=uuid.uuid4,
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        nullable=False,
    )
    commit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True),
        ForeignKey("commits.id"),
        nullable=False,
    )
    blob_sha: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
    )
    language: Mapped[LanguageEnum] = mapped_column(
        SQLAlchemyEnum(LanguageEnum, native_enum=False, length=50), 
        default="unknown",
        index=True,
        nullable=False,
    )
    content_bytes: Mapped[str | None] = mapped_column(LargeBinary, nullable=True)
    embedding: Mapped[list] = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        AwareDateTime, 
        server_default=func.now(), 
        nullable=False,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, 
        default=False,
    )

    commit = relationship("Commit", back_populates="blobs")
    symbols = relationship("Symbol", back_populates="blob", cascade="all, delete-orphan")

    __table_args__ = (
        PrimaryKeyConstraint("id", name="blobs_pkey"),
        ForeignKeyConstraint(
            columns=["commit_id"],
            refcolumns=["commits.id"],
            name="fk_blobs_commit_id",
            ondelete="CASCADE",
        ),
        Index("ix_blobs_repository_id_file_path_is_deleted", "repository_id", "file_path", "is_deleted"),
        Index("ix_blobs_repository_id_language", "repository_id", "language"),
        Index("ix_blobs_repository_id_commit_id_is_deleted", "repository_id", "commit_id", "is_deleted"),
    )