"""ANTLR-backed SQLite smell extractor."""

from __future__ import annotations

import re
from typing import Any

from sqlita.domain.model import SourceUnit
from sqlita.domain.ports import SmellExtractor
from sqlita.domain.smells import DatabaseSmell, SmellReport, SmellSeverity
from sqlita.infrastructure.antlr.runtime import load_generated_types, parse_source_text


class AntlrSqliteSmellExtractor(SmellExtractor):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._generated = load_generated_types()
        self._config = config or {}

    def extract(self, source_unit: SourceUnit) -> SmellReport:
        parse_result = parse_source_text(source_unit.content, self._generated)
        visitor_class = _build_smell_visitor(self._generated.visitor_type, self._config)
        visitor = visitor_class()
        visitor.visit(parse_result.tree)
        visitor.post_process()

        # Global integrity checks
        if not visitor.global_settings.get("FOREIGN_KEYS"):
            visitor.smells.append(
                DatabaseSmell(
                    rule_name="PhantomForeignKey",
                    message="PRAGMA foreign_keys = ON is missing. Foreign keys are silently ignored by default.",
                    severity=SmellSeverity.ERROR,
                    line=1,
                    column=0,
                )
            )

        if not visitor.global_settings.get("WAL"):
            visitor.smells.append(
                DatabaseSmell(
                    rule_name="MissingWAL",
                    message="PRAGMA journal_mode = WAL is missing. SQLite will use slower rollback journal.",
                    severity=SmellSeverity.WARNING,
                    line=1,
                    column=0,
                )
            )
        elif not visitor.global_settings.get("SYNCHRONOUS_NORMAL"):
            visitor.smells.append(
                DatabaseSmell(
                    rule_name="SuboptimalSynchronous",
                    message="PRAGMA synchronous = NORMAL is recommended when using WAL mode for better performance.",
                    severity=SmellSeverity.WARNING,
                    line=1,
                    column=0,
                )
            )

        return SmellReport(
            source_location=source_unit.location,
            smells=tuple(visitor.smells),
        )


def _build_smell_visitor(visitor_base: type, config: dict[str, Any]) -> type:
    god_table_threshold = config.get("god_table_threshold", 15)
    phantom_fk_suffixes = tuple(config.get("phantom_fk_suffixes", ["_id"]))

    class SmellVisitor(visitor_base):
        def __init__(self) -> None:
            super().__init__()
            self.smells: list[DatabaseSmell] = []
            self.global_settings: dict[str, bool] = {
                "FOREIGN_KEYS": False,
                "WAL": False,
                "SYNCHRONOUS_NORMAL": False,
            }

            # Per-table state
            self._current_table_name: str | None = None
            self._current_table_columns: list[str] = []
            self._current_table_col_types: dict[str, str] = {}

            # Missing Index on FK state
            self.foreign_keys: dict[str, set[str]] = {}
            self.indexed_columns: dict[str, set[str]] = {}
            self.fk_locations: dict[tuple[str, str], tuple[int, int]] = {}

        def visitPragma_stmt(self, ctx):
            text = ctx.getText().upper().replace(" ", "")
            if "FOREIGN_KEYS=ON" in text:
                self.global_settings["FOREIGN_KEYS"] = True
            if "JOURNAL_MODE=WAL" in text:
                self.global_settings["WAL"] = True
            if "SYNCHRONOUS=NORMAL" in text:
                self.global_settings["SYNCHRONOUS_NORMAL"] = True
            return self.visitChildren(ctx)

        def visitSelect_stmt(self, ctx):
            text = ctx.getText().upper()
            if "SELECT*" in text or ".*" in text:
                self.smells.append(
                    DatabaseSmell(
                        rule_name="SelectStar",
                        message="SELECT * pulls unnecessary data and breaks on schema changes.",
                        severity=SmellSeverity.WARNING,
                        line=ctx.start.line,
                        column=ctx.start.column,
                    )
                )
            return self.visitChildren(ctx)

        def visitInsert_stmt(self, ctx):
            text = ctx.getText().upper()
            if "VALUES" in text:
                part_before_values = text.split("VALUES")[0]
                if "(" not in part_before_values:
                    self.smells.append(
                        DatabaseSmell(
                            rule_name="ImplicitInsert",
                            message="Implicit column list in INSERT statement. Breaks on schema changes.",
                            severity=SmellSeverity.WARNING,
                            line=ctx.start.line,
                            column=ctx.start.column,
                        )
                    )
            return self.visitChildren(ctx)

        def visitCreate_table_stmt(self, ctx):
            self._current_table_columns = []
            self._current_table_col_types = {}
            self._current_table_name = None

            if hasattr(ctx, "table_name") and callable(ctx.table_name):
                table_name_ctx = ctx.table_name()
                if table_name_ctx is not None:
                    self._current_table_name = table_name_ctx.getText().upper()
                    self.foreign_keys[self._current_table_name] = set()

            res = self.visitChildren(ctx)

            text_upper = ctx.getText().upper()
            normalized_text = re.sub(r"[\s;]", "", text_upper)

            if len(self._current_table_columns) > god_table_threshold:
                self.smells.append(
                    DatabaseSmell(
                        rule_name="GodTable",
                        message=f"Table has {len(self._current_table_columns)} columns, violating Single Responsibility.",
                        severity=SmellSeverity.WARNING,
                        line=ctx.start.line,
                        column=ctx.start.column,
                    )
                )

            # Missing Primary Key
            if "PRIMARYKEY" not in normalized_text:
                self.smells.append(
                    DatabaseSmell(
                        rule_name="MissingPrimaryKey",
                        message=f"Table '{self._current_table_name or 'unnamed'}' has no PRIMARY KEY defined.",
                        severity=SmellSeverity.ERROR,
                        line=ctx.start.line,
                        column=ctx.start.column,
                    )
                )

            # Non-Strict Mode
            if "STRICT" not in normalized_text:
                self.smells.append(
                    DatabaseSmell(
                        rule_name="NonStrictMode",
                        message="Table does not use STRICT mode. Production tables benefit from enforced type checking.",
                        severity=SmellSeverity.WARNING,
                        line=ctx.start.line,
                        column=ctx.start.column,
                    )
                )

            # EAV Check
            cols_lower = [c.lower() for c in self._current_table_columns]
            has_entity_id = any(c.endswith("_id") or c == "id" for c in cols_lower)
            if has_entity_id and "key" in cols_lower and "value" in cols_lower:
                self.smells.append(
                    DatabaseSmell(
                        rule_name="EAVPattern",
                        message="Table contains entity_id + key + value. Entity-Attribute-Value anti-pattern detected.",
                        severity=SmellSeverity.WARNING,
                        line=ctx.start.line,
                        column=ctx.start.column,
                    )
                )

            # Phantom FK Check
            has_fk = "FOREIGNKEY" in normalized_text or "REFERENCES" in normalized_text
            if not has_fk:
                for col in self._current_table_columns:
                    col_lower = col.lower()
                    if any(col_lower.endswith(s) for s in phantom_fk_suffixes):
                        col_type = self._current_table_col_types.get(col, "").upper()
                        if col_type == "" or "INT" in col_type:
                            self.smells.append(
                                DatabaseSmell(
                                    rule_name="PhantomForeignKey",
                                    message=f"Column '{col}' looks like a foreign key but lacks a constraint.",
                                    severity=SmellSeverity.ERROR,
                                    line=ctx.start.line,
                                    column=ctx.start.column,
                                )
                            )

            self._current_table_name = None
            return res

        def visitColumn_def(self, ctx):
            col_name = None
            col_type = ""

            if hasattr(ctx, "column_name") and callable(ctx.column_name):
                col_name_ctx = ctx.column_name()
                if col_name_ctx is not None:
                    col_name = col_name_ctx.getText()
                    self._current_table_columns.append(col_name)

            if hasattr(ctx, "type_name") and callable(ctx.type_name):
                type_name_ctx = ctx.type_name()
                if type_name_ctx is not None:
                    col_type = type_name_ctx.getText()
                    if col_name:
                        self._current_table_col_types[col_name] = col_type

            if col_name:
                name_lower = col_name.lower()
                text_upper = ctx.getText().upper()
                normalized_col = re.sub(r"[\s;]", "", text_upper)

                if "tags" in name_lower or "list" in name_lower or "csv" in name_lower:
                    self.smells.append(
                        DatabaseSmell(
                            rule_name="MultiValueColumn",
                            message=f"Column '{col_name}' suggests multiple values stored in a single string.",
                            severity=SmellSeverity.WARNING,
                            line=ctx.start.line,
                            column=ctx.start.column,
                        )
                    )

                if name_lower == "ref_id" or name_lower == "ref_type":
                    self.smells.append(
                        DatabaseSmell(
                            rule_name="PolymorphicAssociation",
                            message=f"Column '{col_name}' suggests a polymorphic association. Foreign keys cannot enforce integrity.",
                            severity=SmellSeverity.ERROR,
                            line=ctx.start.line,
                            column=ctx.start.column,
                        )
                    )

                if "AUTOINCREMENT" in normalized_col:
                    self.smells.append(
                        DatabaseSmell(
                            rule_name="AutoIncrement",
                            message="AUTOINCREMENT is slower and uses extra space. Use INTEGER PRIMARY KEY instead.",
                            severity=SmellSeverity.WARNING,
                            line=ctx.start.line,
                            column=ctx.start.column,
                        )
                    )

                # CaseSensitiveLookup
                if name_lower in {"email", "login", "username", "user_name"}:
                    if "COLLATENOCASE" not in normalized_col:
                        self.smells.append(
                            DatabaseSmell(
                                rule_name="CaseSensitiveLookup",
                                message=f"Column '{col_name}' likely requires case-insensitive lookups. Consider COLLATE NOCASE.",
                                severity=SmellSeverity.WARNING,
                                line=ctx.start.line,
                                column=ctx.start.column,
                            )
                        )

                # PlaintextSecrets
                if any(s in name_lower for s in {"password", "secret", "token", "api_key"}):
                    self.smells.append(
                        DatabaseSmell(
                            rule_name="PlaintextSecrets",
                            message=f"Column '{col_name}' might store sensitive data in plaintext.",
                            severity=SmellSeverity.WARNING,
                            line=ctx.start.line,
                            column=ctx.start.column,
                        )
                    )

                # NotNullCoverage Smell
                expected_not_null = {"email", "name", "status", "type", "created_at", "updated_at"}
                if (
                    name_lower in expected_not_null
                    or name_lower.endswith("_id")
                    or name_lower == "id"
                ):
                    if "NOTNULL" not in normalized_col and "PRIMARYKEY" not in normalized_col:
                        self.smells.append(
                            DatabaseSmell(
                                rule_name="NotNullCoverage",
                                message=f"Column '{col_name}' typically requires a NOT NULL constraint.",
                                severity=SmellSeverity.WARNING,
                                line=ctx.start.line,
                                column=ctx.start.column,
                            )
                        )

                # DateAsText Smell
                is_date_col = (
                    "date" in name_lower or "time" in name_lower or name_lower.endswith("_at")
                )
                if is_date_col and "TEXT" in col_type.upper():
                    if "CHECK" not in normalized_col:
                        self.smells.append(
                            DatabaseSmell(
                                rule_name="DateAsText",
                                message=f"Column '{col_name}' stores dates as TEXT without a CHECK constraint for format validation.",
                                severity=SmellSeverity.WARNING,
                                line=ctx.start.line,
                                column=ctx.start.column,
                            )
                        )

                # Track foreign keys for Missing Index
                if "REFERENCES" in normalized_col and self._current_table_name:
                    self.foreign_keys[self._current_table_name].add(col_name.upper())
                    self.fk_locations[(self._current_table_name, col_name.upper())] = (
                        ctx.start.line,
                        ctx.start.column,
                    )

            return self.visitChildren(ctx)

        def visitTable_constraint(self, ctx):
            text_upper = ctx.getText().upper()
            normalized_cons = re.sub(r"[\s;]", "", text_upper)
            if "FOREIGNKEY(" in normalized_cons and self._current_table_name:
                match = re.search(r"FOREIGNKEY\(([^)]+)\)", normalized_cons)
                if match:
                    cols = match.group(1).split(",")
                    for c in cols:
                        c_clean = c.strip().strip("'\"[]`").upper()
                        self.foreign_keys[self._current_table_name].add(c_clean)
                        self.fk_locations[(self._current_table_name, c_clean)] = (
                            ctx.start.line,
                            ctx.start.column,
                        )

            return self.visitChildren(ctx)

        def visitCreate_index_stmt(self, ctx):
            if hasattr(ctx, "table_name") and callable(ctx.table_name):
                table_name_ctx = ctx.table_name()
                if table_name_ctx is not None:
                    table_name = table_name_ctx.getText().upper()
                    if table_name not in self.indexed_columns:
                        self.indexed_columns[table_name] = set()

                    if hasattr(ctx, "indexed_column") and callable(ctx.indexed_column):
                        cols = ctx.indexed_column()
                        for col_ctx in cols:
                            if hasattr(col_ctx, "expr") and callable(col_ctx.expr):
                                expr_ctx = col_ctx.expr()
                                if expr_ctx is not None:
                                    self.indexed_columns[table_name].add(expr_ctx.getText().upper())
            return self.visitChildren(ctx)

        def post_process(self) -> None:
            # Check for missing indices on FKs
            for table, fks in self.foreign_keys.items():
                indexed = self.indexed_columns.get(table, set())
                for fk in fks:
                    if fk not in indexed:
                        loc = self.fk_locations.get((table, fk), (0, 0))
                        self.smells.append(
                            DatabaseSmell(
                                rule_name="MissingIndexOnForeignKey",
                                message=f"Foreign key '{fk}' in table '{table}' lacks an index. This can cause full table scans on JOINs or cascading deletes.",
                                severity=SmellSeverity.ERROR,
                                line=loc[0],
                                column=loc[1],
                            )
                        )

    return SmellVisitor
