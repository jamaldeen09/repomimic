import uuid

from typing import Any, Protocol, runtime_checkable
from tree_sitter import Node
from src.repomimic.db.models.symbol import Symbol

@runtime_checkable
class SymbolExtractor(Protocol):
    """Protocol for language-specific symbol extractors."""
    container_types: frozenset[str]
    wrapper_types: frozenset[str]

    def get_node_symbol(
        self,
        node: Node | None = None,
        decorators: list[str] | None = None,
        parent_id: uuid.UUID | None = None,
        parent_breadcrumb: str | None = None,
    ) -> Any | None:
        ...

async def process_and_ingest(
    root_node: Node,
    extractor: SymbolExtractor,
    session: Any,
    repository_id: uuid.UUID,
    blob_id: uuid.UUID,
) -> list:
    """Traverses an AST using a language's symbol extractor and ingests symbols live into the DB.
    
    Completely standalone and language-agnostic. Compatible with any extractor that provides:
    - extractor.get_node_symbol(node, parent_id, parent_breadcrumb)
    - extractor.container_types (frozenset of node types that define a parent scope)
    - extractor.wrapper_types (optional frozenset of wrapper node types, e.g. decorated_definition, export_statement)
    """
    container_types = getattr(extractor, "container_types", frozenset())
    wrapper_types = getattr(extractor, "wrapper_types", frozenset())

    async def walk(current_node: Node, parent_id: uuid.UUID | None = None, parent_breadcrumb: str | None = None):
        symbol = extractor.get_node_symbol(
            node=current_node,
            parent_id=parent_id,
            parent_breadcrumb=parent_breadcrumb,
        )

        current_parent_id = parent_id
        current_breadcrumb = parent_breadcrumb

        if symbol:
            symbol_metadata = (
                symbol.model_dump(
                    exclude={"name", "kind", "id", "parent_symbol_id"},
                    mode="json",
                )
                if hasattr(symbol, "model_dump")
                else {
                    k: v for k, v in symbol.__dict__.items()
                    if k not in ("name", "kind", "id", "parent_symbol_id")
                }
            )

            db_symbol = Symbol(
                id=symbol.id,
                repository_id=repository_id,
                blob_id=blob_id,
                name=symbol.name or "<unnamed>",
                kind=symbol.kind,
                parent_symbol_id=symbol.parent_symbol_id,
                symbol_metadata=symbol_metadata,
                embedding=[0.0] * 1536,
            )

            session.add(db_symbol)
            await session.flush()

            if symbol.kind in container_types:
                current_parent_id = symbol.id
                symbol_name = symbol.name or "<unnamed>"
                breadcrumb_part = f"{symbol.kind} -> {symbol_name}"
                current_breadcrumb = f"{parent_breadcrumb} / {breadcrumb_part}" if parent_breadcrumb else breadcrumb_part

        is_wrapper = current_node.type in wrapper_types
        for i in range(current_node.child_count):
            child = current_node.child(i)
            if not child:
                continue

            if is_wrapper and child.type in container_types:
                body = child.child_by_field_name("body")
                if body:
                    await walk(body, parent_id=current_parent_id, parent_breadcrumb=current_breadcrumb)
            else:
                await walk(child, parent_id=current_parent_id, parent_breadcrumb=current_breadcrumb)

    await walk(root_node)