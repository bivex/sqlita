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

* **Architecture**
  * keeping parser infrastructure behind ports so the application layer stays independent from ANTLR, filesystem, and CLI details

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

## Constraints and honesty

The current ANTLR grammar is sourced from `antlr/grammars-v4/sql/sqlite`. Its own README states that it targets SQLite 3 syntax. Sqlita makes limitations explicit in requirements, ADRs, and runtime metadata so downstream consumers know what contract they are integrating with.

## Next Steps

Useful future extensions:

* semantic passes on top of the structural model
* integration adapters for external analysis tools
* incremental parsing and caching