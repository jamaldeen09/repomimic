import uuid

from sqlalchemy.orm import (
    DeclarativeBase, 
    Mapped, 
    mapped_column, 
    relationship
)
from sqlalchemy import (
    String, 
    Integer, 
    DateTime, 
    func, 
    UniqueConstraint, 
    PrimaryKeyConstraint, 
    CheckConstraint, 
    Index, 
    ForeignKey, 
    ForeignKeyConstraint
)
from sqlalchemy.dialects.postgresql import (UUID , JSONB)
from pgvector.sqlalchemy import Vector
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    default_branch: Mapped[str] = mapped_column(String, nullable=False)

    code_chunks: Mapped[list["CodeChunk"]] = relationship("CodeChunk", back_populates="repository", cascade="all, delete-orphan")

    __table_args__ = (
        PrimaryKeyConstraint("id", name="repositories_pkey"),
        UniqueConstraint("url", name="uq_repositories_url"),
        CheckConstraint(
            "url ~* '^https?://(www\\.)?github\\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$'",
            name="ck_github_repo_url"
        ),
    )

class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
    repository_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    chunk_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="code_chunks")

    __table_args__ = (
        PrimaryKeyConstraint("id", name="code_chunks_pkey"),
        ForeignKeyConstraint(
            name="fk_code_chunks_repository_id",
            columns=["repository_id"],
            refcolumns=["repositories.id"],
            ondelete="CASCADE",
        ),

        Index(
            "ix_code_chunks_embedding",
            embedding,
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_code_chunks_repository_id","repository_id"),
    )
