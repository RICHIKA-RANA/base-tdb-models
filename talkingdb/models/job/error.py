from enum import Enum


class JobErrorCode(str, Enum):
    """`JobErrorCode` remains unchanged and coarse for compatibility with existing SDK clients. 
    Any new user-facing failure details should be added to `FailureReason`, not this enum.
    """

    VALIDATION_ERROR = "VALIDATION_ERROR"   # bad type / too large / bad input
    PARSE_ERROR = "PARSE_ERROR"             # content-elementizer / docx failure
    INDEX_ERROR = "INDEX_ERROR"             # tokenizer / symbol-gen / graph build
    PERSIST_ERROR = "PERSIST_ERROR"         # SQLite write failure
    TIMEOUT = "TIMEOUT"                     # exceeded MAX_JOB_DURATION
    STUCK = "STUCK"                         # heartbeat alive, no progress for too long
    INTERNAL_ERROR = "INTERNAL_ERROR"       # unclassified / orphaned
