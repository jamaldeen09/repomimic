
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
    Uuid,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
)

from datetime import datetime
from pgvector.sqlalchemy import Vector

from .aware_datetime import AwareDateTime
from .base import Base

class Symbol(Base):
    """
    Represents a named symbol in source code (function, class, constant, etc.).
    This is extracted via AST parsing.
    
    Columns:
    - id (PK): Unique internal ID.
    - repository_id: Unique Identifier for a Repository.
    - blob_id (FK): Foreign key to Blob (which file contains this symbol).
    - name: Name of the symbol (e.g., "authenticate").
    - kind: Type of symbol (function, class, constant, etc.).
    - line_start: Starting line number in file.
    - line_end: Ending line number in file.
    - parent_symbol_id (FK): If nested (e.g., method inside a class).
    - docstring: Documentation/docstring if present.
    - return_type: Inferred return type if applicable.
    - parameters: JSON list of parameters with types.
    - embedding: Vector embedding for semantic search.
    - created_at: When this symbol was discovered.
    """
    __tablename__ = "symbols"
    
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True), 
        primary_key=True,
        default=uuid.uuid4,
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(native_uuid=True), 
        nullable=False,
    )
    blob_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("blobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255), 
        index=True,
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
    )
    parent_symbol_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(native_uuid=True), 
        ForeignKey("symbols.id"),
        index=True,
        nullable=True,
    )
    embedding: Mapped[list] = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        AwareDateTime, 
        server_default=func.now(),
        nullable=False
    )
    
    blob = relationship("Blob", back_populates="symbols")
    children = relationship("Symbol", remote_side=[parent_symbol_id], cascade="all, delete-orphan")

    __table_args__ = (
        PrimaryKeyConstraint("id", name="symbols_pkey"),
        ForeignKeyConstraint(
            columns=["blob_id"],
            refcolumns=["blobs.id"],
            name="fk_symbols_blob_id",
            ondelete="CASCADE",
        ),
        Index("ix_symbols_repository_id_name_kind", "repository_id", "name", "kind"),
        Index("ix_symbols_repository_id_kind", "repository_id", "kind"),
    )
