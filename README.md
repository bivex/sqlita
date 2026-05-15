# Sqlita

Sqlita is a simple, scalable monolith for parsing SQLite source code through ANTLR while keeping the architecture clean enough for future semantic analysis, indexing, and export pipelines.

The project starts from the domain, not from the framework:

* business goal: convert SQLite source into a stable structural model for downstream tooling
* architectural style: DDD-inspired layered monolith with hexagonal boundaries
* parser engine: ANTLR4 with the public SQLite grammar from `antlr/grammars-v4`
* current delivery channel: CLI that parses a file or a directory and returns versioned JSON

## What the system does

Today the system supports:

* **Parsing SQLite code**
  * parsing one SQLite file
  * parsing a directory of SQLite files
  * extracting a lightweight structural model: tables, columns, indexes, views, triggers, and statements
  * reporting syntax diagnostics as part of the contract

* **Database Smell Detection**
  * identifying schema and performance anti-patterns (e.g., missing indexes, EAV, phantom foreign keys)
  * outputting detailed JSON reports with line and column references

* **Architecture**
  * keeping parser infrastructure behind ports so the application layer stays independent from ANTLR, filesystem, and CLI details

## Database Smells Detected

Sqlita analyzes the parsed AST to identify common structural, performance, and integrity anti-patterns:

| Rule Name | Severity | Description |
| :--- | :---: | :--- |
| **PhantomForeignKey** | `ERROR` | Missing `PRAGMA foreign_keys = ON` globally, or a column looks like a foreign key (e.g. `user_id` INTEGER) but lacks a constraint. |
| **MissingIndexOnForeignKey**| `ERROR` | A declared `FOREIGN KEY` does not have an accompanying `CREATE INDEX`. In SQLite, this causes full table scans during joins and cascading deletes. |
| **PolymorphicAssociation** | `ERROR` | A table has `ref_id` and `ref_type` columns. Foreign keys cannot enforce referential integrity across multiple target tables. |
| **MissingWAL** | `WARNING` | Missing `PRAGMA journal_mode = WAL`. WAL significantly improves concurrency and performance in most applications. |
| **EAVPattern** | `WARNING` | A table contains an entity ID along with `key` and `value` columns (Entity-Attribute-Value anti-pattern). |
| **MultiValueColumn** | `WARNING` | A column name implies multiple values are stored in a single string (e.g. `tags`, `csv`, `list`). |
| **GodTable** | `WARNING` | A table has more than 15 columns, potentially violating the Single Responsibility Principle. |
| **AutoIncrement** | `WARNING` | Using `AUTOINCREMENT` instead of `INTEGER PRIMARY KEY`. It is slower and uses an extra internal table. |
| **SelectStar** | `WARNING` | Using `SELECT *` fetches unnecessary data and makes the query fragile to schema changes. |
| **ImplicitInsert** | `WARNING` | Using `INSERT INTO table VALUES (...)` without an explicit column list. Breaks when new columns are added. |
| **NotNullCoverage** | `WARNING` | A column typically requiring a value (e.g. `id`, `email`, `status`) lacks a `NOT NULL` constraint. |
| **DateAsText** | `WARNING` | A date or time column is declared as `TEXT` but lacks a `CHECK` constraint to enforce formatting. |
| **MissingPrimaryKey** | `ERROR` | A table has no `PRIMARY KEY` defined. |
| **NonStrictMode** | `WARNING` | Table does not use `STRICT` mode (SQLite 3.37+). `STRICT` enforces strict data typing. |
| **CaseSensitiveLookup** | `WARNING` | Columns like `email` or `username` likely need `COLLATE NOCASE` for correct lookups. |
| **PlaintextSecrets** | `WARNING` | Column names like `password` or `secret` suggest sensitive data stored in plaintext. |
| **SuboptimalSynchronous** | `WARNING` | When using WAL mode, `PRAGMA synchronous = NORMAL` is recommended for better performance. |
| **GodTable** | `WARNING` | A table has more than 15 columns (configurable), violating Single Responsibility. |
| **EAVPattern** | `WARNING` | Table contains `entity_id` + `key` + `value` (Entity-Attribute-Value anti-pattern). |
| **MultiValueColumn** | `WARNING` | A column name implies multiple values stored in a string (e.g. `tags`, `csv`). |

## Architecture

The codebase is split into four explicit layers:

* `domain`: domain model, invariants, ports, and domain events
* `application`: use cases and DTOs
* `infrastructure`: ANTLR adapter, filesystem adapters, event publishing
* `presentation`: CLI contract

See the full design docs in [docs/domain-and-goals.md](docs/domain-and-goals.md), [docs/requirements.md](docs/requirements.md), [docs/system-context.md](docs/system-context.md), [docs/glossary.md](docs/glossary.md), and [docs/architecture.md](docs/architecture.md).

## Quick Start

1. Install dependencies:

```bash
uv sync --extra dev
```

2. Generate the SQLite parser from the vendored grammar:

```bash
uv run python scripts/generate_sqlite_parser.py
```

3. Parse a single file:

```bash
uv run sqlita parse-file path/to/File.sql
```

4. Parse a directory:

```bash
uv run sqlita parse-dir path/to/project
```

5. Detect smells in a file:

```bash
uv run sqlita smells-file path/to/File.sql
```

6. Detect smells in a directory:

```bash
uv run sqlita smells-dir path/to/project
```

## Example Output

```bash
uv run sqlita smells-file schema.sql
```

```json
{
  "source_location": "/path/to/schema.sql",
  "smells": [
    {
      "rule_name": "PhantomForeignKey",
      "message": "Column 'user_id' looks like a foreign key but lacks a constraint.",
      "severity": "error",
      "line": 12,
      "column": 3
    }
  ]
}
```

## Constraints and honesty

The current ANTLR grammar is sourced from `antlr/grammars-v4/sql/sqlite`. Its own README states that it targets SQLite 3 syntax. Sqlita makes limitations explicit in requirements, ADRs, and runtime metadata so downstream consumers know what contract they are integrating with.

## Next Steps

- [ ] `NOT NULL` coverage smell — columns without constraints on non-nullable data
- [ ] Date-as-TEXT smell — unguarded text columns for timestamps
- [ ] Configurable thresholds via `.sqlita.toml`
- [x] `--format` flag: `json` | `text` | `github` | `markdown` (for AI and CLI reading)