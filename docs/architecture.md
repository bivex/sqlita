# Architecture

## Chosen Shape

The system uses a DDD-inspired layered monolith with hexagonal boundaries.

That shape is intentional for two reasons:

* the product is still converging on its core contracts

## Architectural Principles

* model the domain explicitly instead of leaking ANTLR or CLI details inward
* keep ports owned by the inner layers and adapters owned by infrastructure
* separate machine-oriented outputs from human-oriented outputs at the application-service level
* keep generated code and third-party grammar concerns isolated
* prefer immutable records and explicit DTO mapping over hidden framework behavior

## Layers

### Domain

Contains:

* entities and value objects for parsing
* invariants and domain errors
* ports
* domain events

The domain does not know about ANTLR, filesystem paths, HTML, CLI arguments, JSON serializers, or logging backends.

### Application

Contains:

* parse-report commands and DTOs
* orchestration services

Current application services:

* `ParsingJobService`

The application layer coordinates work through ports and publishes parse lifecycle events where relevant.

### Infrastructure

Contains:

* ANTLR grammar integration and parser adapters
* control-flow extraction built on top of the generated parser
* filesystem adapters
* clock, logging, and repository adapters
* parser generation scripts

Important current adapters include:

* `FileSystemSourceRepository`
* `AntlrSQLiteSyntaxParser`
* `StructuredLoggingEventPublisher`
* `SystemClock`
* `InMemoryParsingJobRepository`

Infrastructure implements ports instead of defining the domain shape.

### Presentation

Contains:

* CLI entry points
* command parsing
* output path resolution
* JSON response rendering
* exit-code policy

Current CLI commands:

* `parse-file`
* `parse-dir`
* `nassi-file`
* `nassi-dir`

## Primary Runtime Flows

### Parse Report Flow

1. The CLI resolves a file or directory path.
2. `FileSystemSourceRepository` loads one `SourceUnit` or lists many.
3. `ParsingJobService` creates a `ParsingJob`.
4. `AntlrSQLiteSyntaxParser` parses each source unit into a `ParseOutcome`.
5. The service records outcomes, emits lifecycle events, and completes the job.
6. Application DTO mapping produces `ParsingJobReportDTO`.
7. Presentation serializes the DTO to JSON and chooses an exit code.


1. The CLI resolves a file or directory path and any output path override.
2. `FileSystemSourceRepository` loads source units.
5. Presentation writes one HTML file per source or a full bundle plus index page.
6. Presentation prints JSON metadata about generated artifacts.

## Ports and Adapter Seams

The main ports and their current responsibilities are:

* `SourceRepository`: file loading and directory enumeration
* `SQLiteSyntaxParser`: parse-report production
* `DomainEventPublisher`: lifecycle event publication
* `Clock`: time source abstraction
* `ParsingJobRepository`: persistence seam for completed jobs

These seams are important even in a monolith because they keep the core model independent from tooling choices and make parser replacement or renderer expansion possible later.

## Aggregates and Core Models

### Parsing Aggregate

`ParsingJob` owns:

* the list of source units in the job
* file-level parse outcomes
* completion rules
* success and failure counters derived from outcomes

It does not own:

* filesystem traversal
* parser engine lifecycle
* JSON rendering
* HTML rendering




* no extra persistence lifecycle
* easy reuse by future renderers such as SVG, PNG, or Mermaid

## Error Model

The contract distinguishes:

* business validation errors, such as an empty source set
* technical failures, such as unreadable files or parser runtime failures
* syntax diagnostics, which are parser findings and not process crashes


## State and Persistence

The current system is mostly request-scoped:

* parse jobs are assembled in memory
* generated artifacts are written directly to the filesystem

`InMemoryParsingJobRepository` is a seam, not long-term persistence. It exists so the application layer keeps a stable dependency even before a real repository is needed.

## Why a Monolith

The workload is cohesive, the domain is still forming, and the team benefits more from simplicity and low operational overhead than from distributed decomposition. Bounded contexts remain explicit so the system can split later if a real need appears.

## Evolution Seams

The current architecture leaves room for:

* richer SQLite semantic passes on top of the structural model
* alternate delivery channels such as services, plugins, or IDE integrations
* persistent job storage or cached parse artifacts
* richer observability built on top of existing domain events
