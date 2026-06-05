from enum import Enum


class JobStage(str, Enum):
    """Execution stage of an active ingestion job.

    Stages are only meaningful while a job is actively progressing
    (for example: QUEUED, ONGOING, or CANCELLING).

    Terminal jobs must clear the stage field to ``None`` to avoid
    exposing stale progress information.
    """

    VALIDATING = "VALIDATING"
    PARSING = "PARSING"
    ELEMENT_EXTRACTION = "ELEMENT_EXTRACTION"
    TREE_GENERATION = "TREE_GENERATION"
    INDEXING = "INDEXING"
    PERSISTING = "PERSISTING"
