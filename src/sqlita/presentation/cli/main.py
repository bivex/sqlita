"""CLI application."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlita.application.dto import ParseDirectoryCommand, ParseFileCommand, ParsingJobReportDTO
from sqlita.application.smells import (
    DetectSmellsDirectoryCommand,
    DetectSmellsFileCommand,
    SmellDetectionService,
    SmellReportBundleDTO,
    SmellReportDTO,
)
from sqlita.application.use_cases import ParsingJobService
from sqlita.domain.errors import SqlitaError
from sqlita.infrastructure.antlr.parser_adapter import AntlrSqliteSyntaxParser
from sqlita.infrastructure.antlr.smell_extractor import AntlrSqliteSmellExtractor
from sqlita.infrastructure.filesystem.source_repository import FileSystemSourceRepository
from sqlita.infrastructure.system import (
    InMemoryParsingJobRepository,
    StructuredLoggingEventPublisher,
    SystemClock,
    configure_logging,
)


def _load_config() -> dict[str, object]:
    try:
        import tomllib
    except ImportError:
        return {}

    config_path = Path(".sqlita.toml")
    if config_path.exists():
        with config_path.open("rb") as f:
            try:
                data = tomllib.load(f)
                return data.get("smells", {})
            except Exception:
                pass
    return {}


def main(argv: list[str] | None = None) -> int:
    parser = _build_argument_parser()
    args = parser.parse_args(argv)

    configure_logging(verbose=getattr(args, "verbose", False))

    try:
        if args.command == "parse-file":
            report = _build_parse_service().parse_file(ParseFileCommand(path=args.path))
            exit_code = _exit_code_for(report)
            print(json.dumps(report.to_dict(), indent=2))
        elif args.command == "parse-dir":
            report = _build_parse_service().parse_directory(
                ParseDirectoryCommand(root_path=args.path)
            )
            exit_code = _exit_code_for(report)
            print(json.dumps(report.to_dict(), indent=2))
        elif args.command == "smells-file":
            report = _build_smells_service().detect_file(DetectSmellsFileCommand(path=args.path))
            _print_smells_report(report, getattr(args, "format", "json"))
            exit_code = 0
        elif args.command == "smells-dir":
            report = _build_smells_service().detect_directory(
                DetectSmellsDirectoryCommand(root_path=args.path)
            )
            _print_smells_report(report, getattr(args, "format", "json"))
            exit_code = 0
        else:
            parser.error(f"unsupported command: {args.command}")
    except SqlitaError as error:
        print(json.dumps({"error": str(error)}, indent=2), file=sys.stderr)
        return 2

    return exit_code


def _print_smells_report(report: SmellReportDTO | SmellReportBundleDTO, format_type: str) -> None:
    if format_type == "json":
        print(json.dumps(report.to_dict(), indent=2))
    elif format_type == "text":
        if isinstance(report, SmellReportBundleDTO):
            for r in report.reports:
                for smell in r.smells:
                    print(
                        f"{r.source_location}:{smell.line}:{smell.column}: {smell.severity.upper()}: [{smell.rule_name}] {smell.message}"
                    )
        else:
            for smell in report.smells:
                print(
                    f"{report.source_location}:{smell.line}:{smell.column}: {smell.severity.upper()}: [{smell.rule_name}] {smell.message}"
                )
    elif format_type == "github":
        if isinstance(report, SmellReportBundleDTO):
            for r in report.reports:
                for smell in r.smells:
                    print(
                        f"::{smell.severity} file={r.source_location},line={smell.line},col={smell.column}::{smell.rule_name}: {smell.message}"
                    )
        else:
            for smell in report.smells:
                print(
                    f"::{smell.severity} file={report.source_location},line={smell.line},col={smell.column}::{smell.rule_name}: {smell.message}"
                )


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse SQLite source code with ANTLR.")
    parser.add_argument("--verbose", action="store_true", help="Enable lifecycle logging.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_file = subparsers.add_parser("parse-file", help="Parse one SQLite file.")
    parse_file.add_argument("path", help="Path to a .sql file.")

    parse_dir = subparsers.add_parser("parse-dir", help="Parse all SQLite files in a directory.")
    parse_dir.add_argument("path", help="Path to a directory.")

    smells_file = subparsers.add_parser(
        "smells-file", help="Detect database smells in one SQLite file."
    )
    smells_file.add_argument("path", help="Path to a .sql file.")
    smells_file.add_argument(
        "--format", choices=["json", "text", "github"], default="json", help="Output format."
    )

    smells_dir = subparsers.add_parser(
        "smells-dir", help="Detect database smells in all SQLite files in a directory."
    )
    smells_dir.add_argument("path", help="Path to a directory.")
    smells_dir.add_argument(
        "--format", choices=["json", "text", "github"], default="json", help="Output format."
    )

    return parser


def _build_parse_service() -> ParsingJobService:
    return ParsingJobService(
        source_repository=FileSystemSourceRepository(),
        parser=AntlrSqliteSyntaxParser(),
        event_publisher=StructuredLoggingEventPublisher(),
        clock=SystemClock(),
        job_repository=InMemoryParsingJobRepository(),
    )


def _build_smells_service() -> SmellDetectionService:
    return SmellDetectionService(
        source_repository=FileSystemSourceRepository(),
        extractor=AntlrSqliteSmellExtractor(config=_load_config()),
    )


def _exit_code_for(report: ParsingJobReportDTO) -> int:
    if report.summary.technical_failure_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
