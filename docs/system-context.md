# System Boundaries and Interaction Contexts

## System Purpose

SQLitea owns the flow from SQLite source input to two output families:

* versioned parse reports for machines

It is not a compiler, build system, or semantic analysis engine. It is a source-intelligence tool with explicit contracts around parsing, structural extraction, and control-flow visualization.

## Primary Actors and Neighbor Systems

### Primary Actors

* developers running the CLI locally
* CI pipelines validating or cataloging SQLite source
* downstream tools that consume JSON parse output

### Neighbor Systems

* the local filesystem that stores SQLite input files and generated artifacts
* the vendored ANTLR SQLite grammar and generated parser runtime
* future analysis or indexing systems that may consume SQLitea outputs

## System Boundary

Inside the system boundary:

* source discovery and file loading
* parsing job orchestration
* parser invocation through ports
* structural extraction
* control-flow extraction
* diagnostics normalization
* CLI response assembly and exit-code policy
* structured lifecycle logging for parse workflows

Outside the system boundary:

* IDE behavior and editor integrations
* the SQLite compiler and build graph
* persistent storage systems
* metrics backends and tracing systems
* dashboards and monitoring products
* remote APIs and distributed orchestration

## Interaction Contexts

### 1. Source Discovery Context

Input adapters discover `.sql` files from a filesystem path and supply `SourceUnit` values to the application layer.

Inputs:

* file path
* directory path

Outputs:

* one `SourceUnit`
* or a sequence of `SourceUnit` values

### 2. Parse Report Context

The application layer asks the `SQLiteSyntaxParser` port to parse a `SourceUnit` and maps the result into a stable report DTO.

Inputs:

* `ParseFileCommand`
* `ParseDirectoryCommand`

Outputs:

* `ParsingJobReportDTO`
* machine-readable JSON through the CLI



Inputs:

* raw SQLite function bodies

Outputs:

* immutable control-flow records for each function in the file



Inputs:


Outputs:

* per-file HTML documents
* directory bundles with an index page
* JSON metadata about generated artifacts

### 5. Observability Context

The parse-report workflow emits domain events that infrastructure currently turns into structured logs. This is a boundary seam for future metrics and tracing, not a full monitoring subsystem.

## Data Ownership

SQLitea owns:

* the domain model
* the application DTO contracts
* the generated HTML document structure
* output path conventions for CLI-generated artifacts

SQLitea does not own:

* the authoritative meaning of SQLite semantics
* the lifecycle of source files outside the current execution
* browser rendering engines

## Dependency Direction

Dependencies are one-directional:

* presentation -> application
* infrastructure -> application/domain ports
* application -> domain
* domain -> nothing outside itself

