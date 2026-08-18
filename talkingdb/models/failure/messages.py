from typing import Dict, Iterable

from talkingdb.models.failure.reason import FailureReason
from talkingdb.models.job.error import JobErrorCode


GENERIC_MESSAGE = "Something went wrong while processing your document."


_MESSAGES: Dict[FailureReason, str] = {
    FailureReason.UNSUPPORTED_FILE_TYPE: "This file type isn't supported.",
    FailureReason.FILE_TOO_LARGE: "This file is too large.",
    FailureReason.PASSWORD_PROTECTED: "This document is password-protected.",
    FailureReason.PROCESSING_FAILED: GENERIC_MESSAGE,
}


_ERROR_CODES: Dict[FailureReason, JobErrorCode] = {
    FailureReason.UNSUPPORTED_FILE_TYPE: JobErrorCode.VALIDATION_ERROR,
    FailureReason.FILE_TOO_LARGE: JobErrorCode.VALIDATION_ERROR,
    FailureReason.PASSWORD_PROTECTED: JobErrorCode.PARSE_ERROR,
    FailureReason.PROCESSING_FAILED: JobErrorCode.INTERNAL_ERROR,
}


def message_for(reason: FailureReason) -> str:
    """Return the sentence to show for ``reason``."""
    return _MESSAGES.get(reason, GENERIC_MESSAGE)


def error_code_for(reason: FailureReason) -> JobErrorCode:
    """Return the coarse code stored alongside ``reason``."""
    return _ERROR_CODES.get(reason, JobErrorCode.INTERNAL_ERROR)


def unsupported_file_type_message(supported: Iterable[str]) -> str:
    """Return the unsupported-type sentence, naming what we do accept."""
    types = sorted(supported)
    if not types:
        return _MESSAGES[FailureReason.UNSUPPORTED_FILE_TYPE]

    readable = ", ".join(f".{ext}" for ext in types[:-1])
    listed = f"{readable} and .{types[-1]}" if readable else f".{types[-1]}"
    return f"We only support {listed} files right now."


def file_too_large_message(max_file_size_mb: int) -> str:
    """Return the oversized-file sentence, naming the limit that applied."""
    return f"This file is too large (max {max_file_size_mb} MB)."
