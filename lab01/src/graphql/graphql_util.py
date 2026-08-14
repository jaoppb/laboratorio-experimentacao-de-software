from graphql import parse, print_ast
from graphql.language.ast import (
    FieldNode,
    InlineFragmentNode,
    NameNode,
    SelectionSetNode,
)
from graphql.language.visitor import Visitor, visit


class SweepVisitor(Visitor):
    def enter_inline_fragment(self, node, key, parent, path, ancestors):
        if node.type_condition.name.value == "Repository":
            # Replace all fields with just 'id' for the lightweight sweep
            id_node = FieldNode(name=NameNode(value="id"))
            return InlineFragmentNode(
                type_condition=node.type_condition,
                selection_set=SelectionSetNode(selections=[id_node]),
            )


class ExtractRepositoryVisitor(Visitor):
    def __init__(self):
        super().__init__()
        self.repository_fragment_ast = None

    def enter_inline_fragment(self, node, key, parent, path, ancestors):
        if node.type_condition.name.value == "Repository":
            self.repository_fragment_ast = node


class GraphQLAstModifier:
    @staticmethod
    def generate_sweep_query(graphql_content: str) -> str:
        """
        Parses the base search query and strips out all heavy repository metrics,
        leaving only the 'id' field for a lightning-fast Sweep.
        """
        doc = parse(graphql_content)
        sweep_doc = visit(doc, SweepVisitor())
        return print_ast(sweep_doc)

    @staticmethod
    def generate_hydrate_query(graphql_content: str) -> str:
        """
        Extracts the '... on Repository' block from the search query and builds
        a new nodes(ids: $ids) query to hydrate metrics directly by ID.
        """
        doc = parse(graphql_content)
        visitor = ExtractRepositoryVisitor()
        visit(doc, visitor)

        if not visitor.repository_fragment_ast:
            raise ValueError(
                "Could not find '... on Repository' inline fragment in the GraphQL query."
            )

        repo_fragment_str = print_ast(visitor.repository_fragment_ast)

        hydrate_query = f"""
        query($ids: [ID!]!) {{
          rateLimit {{
            cost
            remaining
            resetAt
          }}
          nodes(ids: $ids) {{
            {repo_fragment_str}
          }}
        }}
        """
        return hydrate_query.strip()
