"""Exit codes and the exception type used for clean CLI errors."""

from __future__ import annotations

EXIT_OK = 0
EXIT_ERROR = 1  # unexpected failure
EXIT_USAGE = 2  # unknown command / bad arguments
EXIT_NOT_FOUND = 3  # missing document or transaction
EXIT_INVALID = 4  # invalid query or argument value
EXIT_CORRUPT = 5  # corrupt or unreadable data
EXIT_NO_STATE = 6  # index / state missing: run `obelisk ingest`


class ObeliskError(Exception):
    """An expected, user-facing error. Carries the process exit code."""

    def __init__(self, message: str, code: int = EXIT_ERROR) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class QueryError(ObeliskError):
    def __init__(self, message: str) -> None:
        super().__init__(message, EXIT_INVALID)
