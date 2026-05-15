"""ANTLR-backed SQLite parser adapter."""

from __future__ import annotations

from time import perf_counter

from sqlita.domain.model import (
    GrammarVersion,
    ParseOutcome,
    ParseStatistics,
    SourceUnit,
    StructuralElement,
    StructuralElementKind,
)
from sqlita.domain.ports import SqlSyntaxParser
from sqlita.infrastructure.antlr.runtime import (
    ANTLR_GRAMMAR_VERSION,
    load_generated_types,
    parse_source_text,
)


class AntlrSqliteSyntaxParser(SqlSyntaxParser):
    def __init__(self) -> None:
        self._generated = load_generated_types()

    @property
    def grammar_version(self) -> GrammarVersion:
        return ANTLR_GRAMMAR_VERSION

    def parse(self, source_unit: SourceUnit) -> ParseOutcome:
        started_at = perf_counter()
        try:
            parse_result = parse_source_text(source_unit.content, self._generated)
            structure_visitor = _build_structure_visitor(self._generated.visitor_type)()
            structure_visitor.visit(parse_result.tree)

            elements = tuple(structure_visitor.elements)
            elapsed_ms = round((perf_counter() - started_at) * 1000, 3)

            return ParseOutcome.success(
                source_unit=source_unit,
                grammar_version=self.grammar_version,
                diagnostics=parse_result.diagnostics,
                structural_elements=elements,
                statistics=ParseStatistics(
                    token_count=len(parse_result.token_stream.tokens),
                    structural_element_count=len(elements),
                    diagnostic_count=len(parse_result.diagnostics),
                    elapsed_ms=elapsed_ms,
                ),
            )
        except Exception as error:
            elapsed_ms = round((perf_counter() - started_at) * 1000, 3)
            return ParseOutcome.technical_failure(
                source_unit=source_unit,
                grammar_version=self.grammar_version,
                message=str(error),
                elapsed_ms=elapsed_ms,
            )


def _build_structure_visitor(visitor_base: type) -> type:
    class SqliteStructureVisitor(visitor_base):
        def __init__(self) -> None:
            super().__init__()
            self.elements: list[StructuralElement] = []
            self._containers: list[str] = []

        def visitCreate_table_stmt(self, ctx):
            if hasattr(ctx, "table_name") and callable(ctx.table_name):
                table_name_ctx = ctx.table_name()
                if table_name_ctx is not None:
                    name = table_name_ctx.getText()
                    self._append(
                        StructuralElementKind.TABLE,
                        name,
                        ctx,
                        signature=f"CREATE TABLE {name}",
                    )
                    return self._with_container(name, lambda: self.visitChildren(ctx))
            return self.visitChildren(ctx)

        def visitColumn_def(self, ctx):
            if hasattr(ctx, "column_name") and callable(ctx.column_name):
                column_name_ctx = ctx.column_name()
                if column_name_ctx is not None:
                    name = column_name_ctx.getText()
                    type_name = ""
                    if (
                        hasattr(ctx, "type_name")
                        and callable(ctx.type_name)
                        and ctx.type_name() is not None
                    ):
                        type_name = " " + ctx.type_name().getText()
                    self._append(
                        StructuralElementKind.COLUMN,
                        name,
                        ctx,
                        signature=f"{name}{type_name}",
                    )
            return self.visitChildren(ctx)

        def visitCreate_index_stmt(self, ctx):
            if hasattr(ctx, "index_name") and callable(ctx.index_name):
                index_name_ctx = ctx.index_name()
                if index_name_ctx is not None:
                    name = index_name_ctx.getText()
                    self._append(
                        StructuralElementKind.INDEX,
                        name,
                        ctx,
                        signature=f"CREATE INDEX {name}",
                    )
            return self.visitChildren(ctx)

        def visitCreate_view_stmt(self, ctx):
            if hasattr(ctx, "view_name") and callable(ctx.view_name):
                view_name_ctx = ctx.view_name()
                if view_name_ctx is not None:
                    name = view_name_ctx.getText()
                    self._append(
                        StructuralElementKind.VIEW,
                        name,
                        ctx,
                        signature=f"CREATE VIEW {name}",
                    )
            return self.visitChildren(ctx)

        def visitCreate_trigger_stmt(self, ctx):
            if hasattr(ctx, "trigger_name") and callable(ctx.trigger_name):
                trigger_name_ctx = ctx.trigger_name()
                if trigger_name_ctx is not None:
                    name = trigger_name_ctx.getText()
                    self._append(
                        StructuralElementKind.TRIGGER,
                        name,
                        ctx,
                        signature=f"CREATE TRIGGER {name}",
                    )
            return self.visitChildren(ctx)

        def visitCreate_virtual_table_stmt(self, ctx):
            if hasattr(ctx, "table_name") and callable(ctx.table_name):
                table_name_ctx = ctx.table_name()
                if table_name_ctx is not None:
                    name = table_name_ctx.getText()
                    self._append(
                        StructuralElementKind.VIRTUAL_TABLE,
                        name,
                        ctx,
                        signature=f"CREATE VIRTUAL TABLE {name}",
                    )
            return self.visitChildren(ctx)

        def visitSelect_stmt(self, ctx):
            self._append(
                StructuralElementKind.SELECT_STMT,
                "select",
                ctx,
                signature="SELECT ...",
            )
            return self.visitChildren(ctx)

        def visitInsert_stmt(self, ctx):
            self._append(
                StructuralElementKind.INSERT_STMT,
                "insert",
                ctx,
                signature="INSERT INTO ...",
            )
            return self.visitChildren(ctx)

        def visitUpdate_stmt(self, ctx):
            self._append(
                StructuralElementKind.UPDATE_STMT,
                "update",
                ctx,
                signature="UPDATE ...",
            )
            return self.visitChildren(ctx)

        def visitDelete_stmt(self, ctx):
            self._append(
                StructuralElementKind.DELETE_STMT,
                "delete",
                ctx,
                signature="DELETE FROM ...",
            )
            return self.visitChildren(ctx)

        def visitAlter_table_stmt(self, ctx):
            self._append(
                StructuralElementKind.ALTER_TABLE_STMT,
                "alter_table",
                ctx,
                signature="ALTER TABLE ...",
            )
            return self.visitChildren(ctx)

        def visitPragma_stmt(self, ctx):
            self._append(
                StructuralElementKind.PRAGMA_STMT,
                "pragma",
                ctx,
                signature="PRAGMA ...",
            )
            return self.visitChildren(ctx)

        def _append(self, kind, name: str, ctx, signature: str | None = None) -> None:
            container = ".".join(self._containers) if self._containers else None
            self.elements.append(
                StructuralElement(
                    kind=kind,
                    name=name,
                    line=ctx.start.line,
                    column=ctx.start.column,
                    container=container,
                    signature=signature,
                )
            )

        def _with_container(self, name: str, callback):
            self._containers.append(name)
            try:
                return callback()
            finally:
                self._containers.pop()

    return SqliteStructureVisitor
