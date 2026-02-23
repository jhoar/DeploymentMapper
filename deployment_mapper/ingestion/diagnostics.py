from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DiagnosticLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(slots=True, frozen=True)
class ImportDiagnostic:
    code: str
    message: str
    level: DiagnosticLevel = DiagnosticLevel.WARNING
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ImportDiagnostics:
    entries: list[ImportDiagnostic] = field(default_factory=list)

    def add(
        self,
        code: str,
        message: str,
        *,
        level: DiagnosticLevel = DiagnosticLevel.WARNING,
        **context: Any,
    ) -> None:
        self.entries.append(ImportDiagnostic(code=code, message=message, level=level, context=context))

    def extend(self, diagnostics: "ImportDiagnostics") -> None:
        self.entries.extend(diagnostics.entries)

    def has_errors(self) -> bool:
        return any(entry.level is DiagnosticLevel.ERROR for entry in self.entries)
