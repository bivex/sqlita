"""Smell detection models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SmellSeverity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class DatabaseSmell:
    rule_name: str
    message: str
    severity: SmellSeverity
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class SmellReport:
    source_location: str
    smells: tuple[DatabaseSmell, ...]


@dataclass(frozen=True, slots=True)
class SmellReportBundle:
    root_path: str
    reports: tuple[SmellReport, ...]
