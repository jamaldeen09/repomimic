import uuid

from pydantic import BaseModel, Field
from typing import TypedDict

class Parameters(TypedDict):
    """Represents a function parameter with name and optional type annotation."""
    name: str
    param_type: str | None

class PySymbol(BaseModel):
    """Base model for Python code symbols with common metadata."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    parent_symbol_id: uuid.UUID | None = None
    parent_breadcrumb: str | None = None
    name: str | None = None
    kind: str
    line_start: int
    line_end: int
    docstring: str | None = None

class PySymbolForFunctionsAndClasses(PySymbol):
    """Symbol model for functions and classes with parameters and return type."""
    parameters: list[Parameters] = []
    return_type: str | None = None
    decorators: list[str] = []

class PySymbolForAssignments(PySymbol):
    """Symbol model for variable assignments with type and value information."""
    operator: str | None = None
    type_annotation: str | None = None
    value_preview: str | None = None

class PySymbolForStatements(PySymbol):
    """Symbol model for statements like imports, returns, and control flow."""
    statement: str | None = None
    child_type: str | None = None