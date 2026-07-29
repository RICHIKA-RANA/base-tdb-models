"""Pure entity for the file <-> graph mapping.

Persistence (SQL) lives in talkingdb.helpers.file_graph.store, per the
Synterex Engineering Handbook Section 12.5 convention - this model stays a
plain data holder.
"""
from typing import Optional
from pydantic import BaseModel


class FileGraphMappingModel(BaseModel):
    rc: str
    file_hash: str
    graph_id: Optional[str] = None
    job_id: str
    filename: Optional[str] = None
    created_at: str
    updated_at: str