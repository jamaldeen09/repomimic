import uuid

from tree_sitter import Node
from .schemas import (
    Parameters, 
    PySymbol, 
    PySymbolForAssignments, 
    PySymbolForFunctionsAndClasses, 
    PySymbolForStatements
)

class PySymbolExtractor():
    """Extracts Python symbols from tree-sitter parse trees."""
    def extract_docstring(self, node: Node) -> str | None:
        """Extracts and cleans the docstring from a function or class definition."""

        def clean_docstring(docstring: str | None) -> str:
            """Removes enclosing triple quotes and trims whitespace from a docstring."""
            cleaned = docstring.strip()
            for quote in ('"""', "'''"):
                if cleaned.startswith(quote) and cleaned.endswith(quote):
                    cleaned = cleaned[len(quote):-len(quote)]
                    break

            return cleaned.strip()
        
        body = node.child_by_field_name("body")
        if body and body.child_count > 0:
            first_stmt = body.children[0]

            if first_stmt.type == "expression_statement":
                string_node = first_stmt.children[0]

                if string_node.type == "string":
                    uncleaned_docstring = string_node.text.decode("utf-8")
                    return clean_docstring(uncleaned_docstring)
                
        return None

    def extract_function_parameters(self, node: Node) -> list[Parameters]:
        """Extracts parameter names and type annotations from a function definition."""
        params_node = node.child_by_field_name("parameters")
        if not params_node:
            return []
        
        params: list[Parameters] = []
        for child in params_node.children:
            if not child.is_named:
                continue

            param_name = None
            param_type = None

            if child.type == "identifier":
                param_name = child.text.decode("utf-8")

            elif child.type in ("typed_parameter", "typed_default_parameter"):
                for sub in child.children:
                    if sub.type == "identifier" and param_name is None:
                        param_name = sub.text.decode("utf-8")

                    elif sub.type == "type":
                        param_type = sub.text.decode("utf-8")

            params.append({"name": param_name or "", "param_type": param_type})

        return params

    def handle_decorated_definitions (
        self, 
        node: Node, 
        parent_id: uuid.UUID | None = None, 
        parent_breadcrumb: str | None = None
    ) -> PySymbol | None:
        """Handles decorated definitions by extracting decorators and processing the underlying definition."""
        decorators = [
            definition.text.decode("utf-8").strip()
            for definition in node.children
            if definition.type == "decorator"
        ]

        definition_node = node.child_by_field_name("definition")
        if definition_node:
            return self.get_node_symbol(
                definition_node,
                decorators=decorators,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        else:
            return None
        
    def handle_functions_and_classes_definitions(
        self, 
        node: Node,
        line_start: int,
        line_end: int,
        parent_id: uuid.UUID | None = None,
        parent_breadcrumb: str | None = None,
        decorators: list[str] = []
    ) -> PySymbol:
        """Extracts symbol information for function and class definitions."""
        name_node = node.child_by_field_name("name")
        name = name_node.text.decode("utf-8") if name_node else "<unnamed>"
        return_type_node = node.child_by_field_name("return_type")
        return_type = return_type_node.text.decode("utf-8") if return_type_node else None
        docstring = self.extract_docstring(node)
        params = self.extract_function_parameters(node) if "function" in node.type else []

        return PySymbolForFunctionsAndClasses(
            parent_symbol_id=parent_id,
            parent_breadcrumb=parent_breadcrumb,
            name=name,
            kind=node.type,
            return_type=return_type,
            docstring=docstring,
            parameters=params,
            line_start=line_start,
            line_end=line_end,
            decorators=decorators,
        )

    def handle_assignments(
        self,
        node: Node,
        line_start: int,
        line_end: int,
        parent_id: uuid.UUID | None = None,
        parent_breadcrumb: str | None = None,
    ) -> PySymbolForAssignments:
        """Extracts symbol information for variable assignments and augmented assignments."""
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        type_node = node.child_by_field_name("type")
        name = left.text.decode("utf-8") if left else None
        value_preview = right.text.decode("utf-8")[:60].replace("\n", "\\n") if right else None
        type_annotation = type_node.text.decode("utf-8") if type_node else None
        operator = None
        for child in node.children:
            if not child.is_named and child.type not in ("(", ")", "[", "]"):
                operator = child.type
                break

        return PySymbolForAssignments(
            parent_symbol_id=parent_id,
            parent_breadcrumb=parent_breadcrumb,
            name=name,
            kind=node.type,
            type_annotation=type_annotation,
            value_preview=value_preview,
            operator=operator,
            line_start=line_start,
            line_end=line_end,
        )

    def handle_imports(
        self,
        node: Node,
        line_start: int,
        line_end: int,
        parent_id: uuid.UUID | None = None,
        parent_breadcrumb: str | None = None,
    ) -> PySymbolForStatements:
        """Extracts symbol information for import statements."""
        statement_text = node.text.decode("utf-8").replace("\n", " ")[:80]
        return PySymbolForStatements(
            parent_symbol_id=parent_id,
            parent_breadcrumb=parent_breadcrumb,
            kind=node.type,
            statement=statement_text,
            line_start=line_start,
            line_end=line_end,
        )

    def handle_type_aliases(
        self,
        node: Node,
        line_start: int,
        line_end: int,
        parent_id: uuid.UUID | None = None,
        parent_breadcrumb: str | None = None,
    ) -> PySymbolForStatements:
        """Extracts symbol information for type alias statements."""
        statement_text = node.text.decode("utf-8")[:80]
        return PySymbolForStatements(
            parent_symbol_id=parent_id,
            parent_breadcrumb=parent_breadcrumb,
            kind=node.type,
            statement=statement_text,
            line_start=line_start,
            line_end=line_end,
        )

    def handle_return_assert_raise(
        self,
        node: Node,
        line_start: int,
        line_end: int,
        parent_id: uuid.UUID | None = None,
        parent_breadcrumb: str | None = None,
    ) -> PySymbolForStatements:
        """Extracts symbol information for return, assert, and raise statements."""
        value = node.text.decode("utf-8")[:80].replace("\n", "\\n")
        return PySymbolForStatements(
            parent_symbol_id=parent_id,
            parent_breadcrumb=parent_breadcrumb,
            kind=node.type,
            statement=value,
            line_start=line_start,
            line_end=line_end,
        )

    def handle_expressions(
        self,
        node: Node,
        line_start: int,
        line_end: int,
        parent_id: uuid.UUID | None = None,
        parent_breadcrumb: str | None = None,
    ) -> PySymbolForStatements | None:
        """Extracts symbol information for expression statements, excluding string literals."""
        child = node.children[0] if node.children else None
        child_type = child.type if child else "empty"
        if child_type == "string":
            return None
        text = node.text.decode("utf-8")[:80].replace("\n", "\\n")
        return PySymbolForStatements(
            parent_symbol_id=parent_id,
            parent_breadcrumb=parent_breadcrumb,
            kind=node.type,
            child_type=child_type,
            statement=text,
            line_start=line_start,
            line_end=line_end,
        )

    def handle_global_nonlocal(
        self,
        node: Node,
        line_start: int,
        line_end: int,
        parent_id: uuid.UUID | None = None,
        parent_breadcrumb: str | None = None,
    ) -> PySymbolForStatements:
        """Extracts symbol information for global and nonlocal statements."""
        names = [c.text.decode("utf-8") for c in node.children if c.type == "identifier"]
        statement_text = ", ".join(names)
        return PySymbolForStatements(
            parent_symbol_id=parent_id,
            parent_breadcrumb=parent_breadcrumb,
            kind=node.type,
            statement=statement_text,
            line_start=line_start,
            line_end=line_end,
        )

    def handle_delete(
        self,
        node: Node,
        line_start: int,
        line_end: int,
        parent_id: uuid.UUID | None = None,
        parent_breadcrumb: str | None = None,
    ) -> PySymbolForStatements:
        """Extracts symbol information for delete statements."""
        text = node.text.decode("utf-8")[:80]
        return PySymbolForStatements(
            parent_symbol_id=parent_id,
            parent_breadcrumb=parent_breadcrumb,
            kind=node.type,
            statement=text,
            line_start=line_start,
            line_end=line_end,
        )

    def handle_control_flow(
        self,
        node: Node,
        line_start: int,
        line_end: int,
        parent_id: uuid.UUID | None = None,
        parent_breadcrumb: str | None = None,
    ) -> PySymbolForStatements:
        """Extracts symbol information for control flow statements (if, for, while, try, with, match)."""
        first_line = node.text.decode("utf-8").split("\n")[0][:80]
        return PySymbolForStatements(
            parent_symbol_id=parent_id,
            parent_breadcrumb=parent_breadcrumb,
            kind=node.type,
            statement=first_line,
            line_start=line_start,
            line_end=line_end,
        )

    def get_node_symbol(
        self,
        node: Node | None = None,
        decorators: list[str] | None = None,
        parent_id: uuid.UUID | None = None,
        parent_breadcrumb: str | None = None,
    ) -> PySymbol | None:
        """Dispatches to the appropriate handler based on node type to extract symbol information."""
        if not node:
            return None

        line_start = node.start_point[0] + 1
        line_end = node.end_point[0] + 1

        if node.type == "decorated_definition":
            return self.handle_decorated_definitions(
                node=node,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        if node.type in ("function_definition", "class_definition", "async_function_definition"):
            return self.handle_functions_and_classes_definitions(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
                decorators=decorators or [],
            )

        elif node.type in ("assignment", "augmented_assignment"):
            return self.handle_assignments(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        elif node.type in ("import_statement", "import_from_statement"):
            return self.handle_imports(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        elif node.type == "type_alias_statement":
            return self.handle_type_aliases(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        elif node.type in ("return_statement", "assert_statement", "raise_statement"):
            return self.handle_return_assert_raise(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        elif node.type == "expression_statement":
            return self.handle_expressions(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        elif node.type in ("global_statement", "nonlocal_statement"):
            return self.handle_global_nonlocal(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        elif node.type == "delete_statement":
            return self.handle_delete(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        elif node.type in ("if_statement", "for_statement", "while_statement",
                            "try_statement", "with_statement", "match_statement",
                            "async_for_statement", "async_with_statement"):
            return self.handle_control_flow(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        return None

