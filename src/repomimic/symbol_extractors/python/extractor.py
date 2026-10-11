import uuid

from tree_sitter import Node
from .schemas import (
    Parameters, 
    PySymbol, 
    PySymbolForAssignments, 
    PySymbolForFunctionsAndClasses, 
    PySymbolForStatements
)

FUNCTION_AND_CLASS_TYPES = frozenset({"function_definition", "class_definition", "async_function_definition"})
FUNCTION_TYPES = frozenset({"function_definition", "async_function_definition"})
ASSIGNMENT_TYPES = frozenset({"assignment", "augmented_assignment"})
IMPORT_TYPES = frozenset({"import_statement", "import_from_statement"})
RETURN_ASSERT_RAISE_TYPES = frozenset({"return_statement", "assert_statement", "raise_statement"})
GLOBAL_NONLOCAL_TYPES = frozenset({"global_statement", "nonlocal_statement"})
CONTROL_FLOW_TYPES = frozenset({
    "if_statement", "for_statement", "while_statement",
    "try_statement", "with_statement", "match_statement",
    "async_for_statement", "async_with_statement"
})
PARAM_TYPED_TYPES = frozenset({"typed_parameter", "typed_default_parameter"})
PARAM_DEFAULT_TYPES = frozenset({"default_parameter"})
BRACKET_PUNCTUATION = frozenset({"(" , ")", "[", "]"})

class PySymbolExtractor():
    """Extracts Python symbols from tree-sitter parse trees with high-performance lookups and bounded byte slicing."""

    @staticmethod
    def _clean_docstring(docstring: str) -> str:
        """Removes enclosing triple quotes or single quotes and trims whitespace."""
        cleaned = docstring.strip()
        if len(cleaned) >= 6:
            if (cleaned.startswith('"""') and cleaned.endswith('"""')) or (cleaned.startswith("'''") and cleaned.endswith("'''")):
                return cleaned[3:-3].strip()
        elif len(cleaned) >= 2:
            if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
                return cleaned[1:-1].strip()
        return cleaned

    def extract_docstring(self, node: Node) -> str | None:
        """Extracts and cleans the docstring from a function or class definition."""
        body = node.child_by_field_name("body")
        if not body or body.child_count == 0:
            return None
        
        first_stmt = body.child(0)
        if not first_stmt or first_stmt.type != "expression_statement" or first_stmt.child_count == 0:
            return None

        string_node = first_stmt.child(0)
        if not string_node or string_node.type != "string":
            return None

        uncleaned_docstring = string_node.text.decode("utf-8", errors="replace")
        return self._clean_docstring(uncleaned_docstring)

    def extract_function_parameters(self, node: Node) -> list[Parameters]:
        """Extracts parameter names and type annotations from a function definition."""
        params_node = node.child_by_field_name("parameters")
        if not params_node:
            return []

        params: list[Parameters] = []
        for i in range(params_node.named_child_count):
            child = params_node.named_child(i)
            if not child:
                continue

            param_name: str | None = None
            param_type: str | None = None
            child_type = child.type

            if child_type == "identifier":
                param_name = child.text.decode("utf-8")

            elif child_type in PARAM_TYPED_TYPES:
                name_node = child.child_by_field_name("name")
                type_node = child.child_by_field_name("type")
                if name_node:
                    param_name = name_node.text.decode("utf-8")
                if type_node:
                    param_type = type_node.text.decode("utf-8")
                if not param_name:
                    for j in range(child.named_child_count):
                        sub = child.named_child(j)
                        if sub.type == "identifier" and param_name is None:
                            param_name = sub.text.decode("utf-8")
                        elif sub.type == "type" and param_type is None:
                            param_type = sub.text.decode("utf-8")

            elif child_type in PARAM_DEFAULT_TYPES:
                name_node = child.child_by_field_name("name")
                if name_node:
                    param_name = name_node.text.decode("utf-8")
                elif child.named_child_count > 0:
                    first = child.named_child(0)
                    if first and first.type == "identifier":
                        param_name = first.text.decode("utf-8")

            params.append({"name": param_name or "", "param_type": param_type})

        return params

    def handle_decorated_definitions(
        self, 
        node: Node, 
        parent_id: uuid.UUID | None = None, 
        parent_breadcrumb: str | None = None
    ) -> PySymbol | None:
        """Handles decorated definitions by extracting decorators and processing the underlying definition."""
        decorators: list[str] = []
        for i in range(node.named_child_count):
            child = node.named_child(i)
            if child and child.type == "decorator":
                decorators.append(child.text.decode("utf-8").strip())

        definition_node = node.child_by_field_name("definition")
        if definition_node:
            return self.get_node_symbol(
                definition_node,
                decorators=decorators,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        return None
        
    def handle_functions_and_classes_definitions(
        self, 
        node: Node,
        line_start: int,
        line_end: int,
        parent_id: uuid.UUID | None = None,
        parent_breadcrumb: str | None = None,
        decorators: list[str] | None = None
    ) -> PySymbol:
        """Extracts symbol information for function and class definitions."""
        name_node = node.child_by_field_name("name")
        name = name_node.text.decode("utf-8") if name_node else "<unnamed>"
        return_type_node = node.child_by_field_name("return_type")
        return_type = return_type_node.text.decode("utf-8") if return_type_node else None
        docstring = self.extract_docstring(node)
        params = self.extract_function_parameters(node) if node.type in FUNCTION_TYPES else []

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
            decorators=decorators or [],
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
        if right:
            raw_bytes = right.text
            if len(raw_bytes) > 120:
                raw_bytes = raw_bytes[:120]
            value_preview = raw_bytes.decode("utf-8", errors="replace")[:60].replace("\n", "\\n")
        else:
            value_preview = None

        type_annotation = type_node.text.decode("utf-8") if type_node else None

        operator = None
        for i in range(node.child_count):
            child = node.child(i)
            if child and not child.is_named and child.type not in BRACKET_PUNCTUATION:
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
        raw_bytes = node.text
        if len(raw_bytes) > 160:
            raw_bytes = raw_bytes[:160]
        statement_text = raw_bytes.decode("utf-8", errors="replace").replace("\n", " ")[:80]

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
        raw_bytes = node.text
        if len(raw_bytes) > 160:
            raw_bytes = raw_bytes[:160]
        statement_text = raw_bytes.decode("utf-8", errors="replace")[:80]

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
        raw_bytes = node.text
        if len(raw_bytes) > 160:
            raw_bytes = raw_bytes[:160]
        value = raw_bytes.decode("utf-8", errors="replace")[:80].replace("\n", "\\n")

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
        if node.child_count == 0:
            return None

        child = node.child(0)
        child_type = child.type if child else "empty"
        if child_type == "string":
            return None

        raw_bytes = node.text
        if len(raw_bytes) > 160:
            raw_bytes = raw_bytes[:160]
        text = raw_bytes.decode("utf-8", errors="replace")[:80].replace("\n", "\\n")

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
        names = [
            node.named_child(i).text.decode("utf-8")
            for i in range(node.named_child_count)
            if node.named_child(i) and node.named_child(i).type == "identifier"
        ]
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
        raw_bytes = node.text
        if len(raw_bytes) > 160:
            raw_bytes = raw_bytes[:160]
        text = raw_bytes.decode("utf-8", errors="replace")[:80]

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
        """Extracts symbol information for control flow statements without decoding the entire block."""
        raw_bytes = node.text
        newline_pos = raw_bytes.find(b"\n")
        if newline_pos != -1:
            raw_line = raw_bytes[:min(newline_pos, 160)]
        else:
            raw_line = raw_bytes[:160]
        first_line = raw_line.decode("utf-8", errors="replace")[:80]

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
        """Dispatches to the appropriate handler using frozenset lookups."""
        if not node:
            return None

        node_type = node.type

        if node_type == "decorated_definition":
            return self.handle_decorated_definitions(
                node=node,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        if node_type in FUNCTION_AND_CLASS_TYPES:
            line_start = node.start_point[0] + 1
            line_end = node.end_point[0] + 1
            return self.handle_functions_and_classes_definitions(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
                decorators=decorators,
            )

        elif node_type in ASSIGNMENT_TYPES:
            line_start = node.start_point[0] + 1
            line_end = node.end_point[0] + 1
            return self.handle_assignments(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        elif node_type in IMPORT_TYPES:
            line_start = node.start_point[0] + 1
            line_end = node.end_point[0] + 1
            return self.handle_imports(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        elif node_type == "type_alias_statement":
            line_start = node.start_point[0] + 1
            line_end = node.end_point[0] + 1
            return self.handle_type_aliases(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        elif node_type in RETURN_ASSERT_RAISE_TYPES:
            line_start = node.start_point[0] + 1
            line_end = node.end_point[0] + 1
            return self.handle_return_assert_raise(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        elif node_type == "expression_statement":
            line_start = node.start_point[0] + 1
            line_end = node.end_point[0] + 1
            return self.handle_expressions(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        elif node_type in GLOBAL_NONLOCAL_TYPES:
            line_start = node.start_point[0] + 1
            line_end = node.end_point[0] + 1
            return self.handle_global_nonlocal(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        elif node_type == "delete_statement":
            line_start = node.start_point[0] + 1
            line_end = node.end_point[0] + 1
            return self.handle_delete(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        elif node_type in CONTROL_FLOW_TYPES:
            line_start = node.start_point[0] + 1
            line_end = node.end_point[0] + 1
            return self.handle_control_flow(
                node=node,
                line_start=line_start,
                line_end=line_end,
                parent_id=parent_id,
                parent_breadcrumb=parent_breadcrumb,
            )

        return None


