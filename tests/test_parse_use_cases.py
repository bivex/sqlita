import json
import subprocess
import sys
from pathlib import Path

from sqlita.application.dto import ParseDirectoryCommand, ParseFileCommand
from sqlita.application.use_cases import ParsingJobService
from sqlita.infrastructure.antlr.parser_adapter import AntlrSqliteSyntaxParser
from sqlita.infrastructure.filesystem.source_repository import FileSystemSourceRepository
from sqlita.infrastructure.system import (
    InMemoryParsingJobRepository,
    StructuredLoggingEventPublisher,
    SystemClock,
)


ROOT = Path(__file__).resolve().parent.parent


def _ensure_generated_parser() -> None:
    generated_parser = (
        ROOT
        / "src"
        / "sqlita"
        / "infrastructure"
        / "antlr"
        / "generated"
        / "sqlite"
        / "SQLiteParser.py"
    )
    if generated_parser.exists():
        return
    subprocess.run(
        [sys.executable, "scripts/generate_sqlite_parser.py"],
        cwd=ROOT,
        check=True,
    )


def _build_service() -> ParsingJobService:
    _ensure_generated_parser()
    return ParsingJobService(
        source_repository=FileSystemSourceRepository(),
        parser=AntlrSqliteSyntaxParser(),
        event_publisher=StructuredLoggingEventPublisher(),
        clock=SystemClock(),
        job_repository=InMemoryParsingJobRepository(),
    )


def test_parse_file_extracts_structure() -> None:
    service = _build_service()
    report = service.parse_file(
        ParseFileCommand(path=str(ROOT / "tests" / "fixtures" / "valid.sql"))
    )

    assert report.summary.source_count == 1
    assert report.summary.technical_failure_count == 0
    assert report.sources[0].status in {"succeeded", "succeeded_with_diagnostics"}
    assert {element.kind for element in report.sources[0].structural_elements} >= {
        "table",
        "column",
        "index",
        "view",
        "insert_stmt",
        "select_stmt",
        "update_stmt",
    }


def test_parse_directory_returns_report_for_all_files() -> None:
    service = _build_service()
    report = service.parse_directory(
        ParseDirectoryCommand(root_path=str(ROOT / "tests" / "fixtures"))
    )

    assert report.summary.source_count == 2
    assert len(report.sources) == 2


def test_parse_file_handles_create_table(tmp_path: Path) -> None:
    service = _build_service()
    source_path = tmp_path / "test.sql"
    source_path.write_text(
        """
CREATE TABLE users (
    id INTEGER PRIMARY KEY
);
""".strip(),
        encoding="utf-8",
    )

    report = service.parse_file(ParseFileCommand(path=str(source_path)))

    assert report.summary.source_count == 1
    assert report.summary.technical_failure_count == 0
    assert {element.kind for element in report.sources[0].structural_elements} >= {
        "table",
        "column",
    }


def test_cli_outputs_json() -> None:
    _ensure_generated_parser()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "sqlita.presentation.cli.main",
            "parse-file",
            str(ROOT / "tests" / "fixtures" / "valid.sql"),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["summary"]["source_count"] == 1
