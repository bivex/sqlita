"""Smell detection use cases."""

from __future__ import annotations

from dataclasses import dataclass

from sqlita.domain.ports import SmellExtractor, SourceRepository
from sqlita.domain.smells import SmellReport


@dataclass(frozen=True, slots=True)
class DetectSmellsFileCommand:
    path: str


@dataclass(frozen=True, slots=True)
class DetectSmellsDirectoryCommand:
    root_path: str


@dataclass(frozen=True, slots=True)
class DatabaseSmellDTO:
    rule_name: str
    message: str
    severity: str
    line: int
    column: int

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_name": self.rule_name,
            "message": self.message,
            "severity": self.severity,
            "line": self.line,
            "column": self.column,
        }


@dataclass(frozen=True, slots=True)
class SmellReportDTO:
    source_location: str
    smells: tuple[DatabaseSmellDTO, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "source_location": self.source_location,
            "smells": [smell.to_dict() for smell in self.smells],
        }


@dataclass(frozen=True, slots=True)
class SmellReportBundleDTO:
    root_path: str
    reports: tuple[SmellReportDTO, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "root_path": self.root_path,
            "reports": [report.to_dict() for report in self.reports],
        }


@dataclass(slots=True)
class SmellDetectionService:
    source_repository: SourceRepository
    extractor: SmellExtractor

    def detect_file(self, command: DetectSmellsFileCommand) -> SmellReportDTO:
        source_unit = self.source_repository.load_file(command.path)
        report = self.extractor.extract(source_unit)
        return _map_report(report)

    def detect_directory(self, command: DetectSmellsDirectoryCommand) -> SmellReportBundleDTO:
        source_units = self.source_repository.list_sql_sources(command.root_path)
        reports = tuple(self.extractor.extract(unit) for unit in source_units)
        return SmellReportBundleDTO(
            root_path=command.root_path,
            reports=tuple(_map_report(r) for r in reports),
        )


def _map_report(report: SmellReport) -> SmellReportDTO:
    return SmellReportDTO(
        source_location=report.source_location,
        smells=tuple(
            DatabaseSmellDTO(
                rule_name=smell.rule_name,
                message=smell.message,
                severity=smell.severity.value,
                line=smell.line,
                column=smell.column,
            )
            for smell in report.smells
        ),
    )
