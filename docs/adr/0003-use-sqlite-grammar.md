# ADR 0003: Replace Swift 5 Grammar with SQLite Grammar

## Context

The initial goal of the project was to parse Swift source code using the public ANTLR Swift 5 grammar. After a strategic pivot, the business goal shifted towards database schema inspection and parsing. Instead of maintaining two completely separate parser bases, we decided to reuse the same robust, hexagonal architecture to parse SQL files.

## Decision

We will replace the Swift 5 grammar with the SQLite grammar from the public `antlr/grammars-v4` repository (`antlr/grammars-v4/sql/sqlite`).
The control-flow extraction and Nassi-Shneiderman diagram features will be completely removed, and the structural domain model will be updated to reflect SQLite constructs (e.g., TABLE, COLUMN, INDEX, VIEW).

## Consequences

* **Positive:** The system's layered architecture proved robust enough to swap out the entire parsing domain and tooling without restructuring the CLI or infrastructure abstraction interfaces.
* **Positive:** The SQLite grammar is much simpler and native to Python, meaning we do not need the complex patching and support-module rewriting we needed for the Swift 5 grammar.
* **Negative:** All Swift-specific features, including structural tracking and visualizations, are retired from this codebase.