from typing import Optional

from talkingdb.models.failure.reason import FailureReason


class DocumentFailure(Exception):
    """A failure whose cause is already known at the point of detection."""

    def __init__(
        self,
        reason: FailureReason,
        detail: Optional[str] = None,
    ) -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(detail or reason.value)
