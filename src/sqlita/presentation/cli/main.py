"""CLI application."""

from __future__ import annotations

import argparse
import json
import sys

from sqlita.application.dto import ParseDirectoryCommand, ParseFileCommand, ParsingJobReportDTO
from sqlita.application.smells import DetectSmellsDirectoryCommand, DetectSmellsFileCommand, SmellDetectionService
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


def main(argv: list[str] | None = None) -> int:
    parser = _build_argument_parser()
    args = parser.parse_args(argv)

    configure_logging(verbose=getattr(args, "verbose", False))

    try:
        if args.command == "parse-file":
            report = _build_parse_service().parse_file(ParseFileCommand(path=args.path))
            exit_code = _exit_code_for(report)
        elif args.command == "parse-dir":
            report = _build_parse_service().parse_directory(
                ParseDirectoryCommand(root_path=args.path)
            )
            exit_code = _exit_code_for(report)
        elif args.command == "smells-file":
            report = _build_smells_service().detect_file(DetectSmellsFileCommand(path=args.path))
            exit_code = 0
        elif args.command == "smells-dir":
            report = _build_smells_service().detect_directory(DetectSmellsDirectoryCommand(root_path=args.path))
            exit_code = 0
        else:
            parser.error(f"unsupported command: {args.command}")
    except SqlitaError as error:
        print(json.dumps({"error": str(error)}, indent=2), file=sys.stderr)
        return 2

    print(json.dumps(report.to_dict(), indent=2))
    return exit_code


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse SQLite source code with ANTLR.")
    parser.add_argument("--verbose", action="store_true", help="Enable lifecycle logging.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_file = subparsers.add_parser("parse-file", help="Parse one SQLite file.")
    parse_file.add_argument("path", help="Path to a .sql file.")

    parse_dir = subparsers.add_parser("parse-dir", help="Parse all SQLite files in a directory.")
    parse_dir.add_argument("path", help="Path to a directory.")

    smells_file = subparsers.add_parser("smells-file", help="Detect database smells in one SQLite file.")
    smells_file.add_argument("path", help="Path to a .sql file.")

    smells_dir = subparsers.add_parser("smells-dir", help="Detect database smells in all SQLite files in a directory.")
    smells_dir.add_argument("path", help="Path to a directory.")

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
        extractor=AntlrSqliteSmellExtractor(),
    )


def _exit_code_for(report: ParsingJobReportDTO) -> int:
    if report.summary.technical_failure_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
