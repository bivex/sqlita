# Glossary and Ubiquitous Language

## Terms

`Parsing Job`
: One execution that processes one or more source units and produces aggregated parse outcomes.

`Source Unit`
: One SQLite source file treated as an addressable input with stable identity, location, and content.

`Parse Outcome`
: The immutable result of parsing one source unit, including status, diagnostics, structural elements, and statistics.

`Parse Status`
: The outcome classification for one source unit: succeeded, succeeded with diagnostics, or technical failure.

`Structural Model`
: The normalized representation of source structure that downstream automation can consume.

`Structural Element`
: One extracted item in the structural model, such as an import, type alias, class, struct, enum, protocol, extension, function, variable, or constant.

`Syntax Diagnostic`
: A parser-reported issue with location, severity, and message.

`Grammar Version`
: The version label of the grammar contract used to parse a source unit.

`Report Schema Version`
: The version label of the parse-report contract exposed to consumers.



: One structured statement-like unit in the control-flow model.


: The generated HTML artifact and metadata for one source file.


`Port`
: An inward-facing interface owned by the domain or application layer.

`Adapter`
: An outward-facing implementation of a port that talks to a concrete technology.

`Source Repository`
: The boundary that loads one file or enumerates SQLite files from a root path.

`SQLite Syntax Parser`
: The boundary that turns a `SourceUnit` into a `ParseOutcome`.



`Boundary Validation`
: Validation performed when data enters or leaves the system.

## Naming Rules

* Use `ParsingJob`, not `TaskManager`.
* Use `SourceUnit`, not `FileData`.
* Use `ParseOutcome`, not `ResultBlob`.
* Use `StructuralElement`, not `NodeInfo`.
* Use `SQLiteSyntaxParser`, not `ParserHelper`.
* Use `SourceRepository`, not `FileUtils`.
