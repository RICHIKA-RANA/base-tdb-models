from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Type

import networkx as nx
from smart_slugify import slugify
from networkx.readwrite import json_graph

@dataclass
class EntityModel:
    entity_id: str
    graph: nx.MultiDiGraph
    _surface_text_index: dict = field(
        default_factory=lambda: defaultdict(set),
        repr=False,
    )

    @staticmethod
    def make_id(name: str) -> str:
        return f"entity::{slugify(name)}"

    @classmethod
    def create(
        cls: Type["EntityModel"],
        entity_id: str,
    ) -> "EntityModel":
        return cls(
            entity_id=entity_id,
            graph=nx.MultiDiGraph(),
        )

    @classmethod
    def load(
        cls: Type["EntityModel"],
        conn: sqlite3.Connection,
        entity_id: str,
    ) -> "EntityModel":
        graph = nx.MultiDiGraph()

        cursor = conn.cursor()

        for node_id, label, surface_texts in cursor.execute(
            """
            SELECT
                node_id,
                label,
                surface_texts
            FROM entities
            WHERE entity_id = ?
            """,
            (entity_id,),
        ):
            graph.add_node(
                node_id,
                label=label,
                surface_texts=json.loads(
                    surface_texts or "[]"
                ),
            )

        for (
            fact_id,
            source,
            target,
            predicate,
            attributes,
        ) in cursor.execute(
            """
            SELECT
                fact_id,
                source,
                target,
                predicate,
                attributes
            FROM facts
            WHERE entity_id = ?
            """,
            (entity_id,),
        ):
            attrs = json.loads(attributes or "{}")
            attrs["predicate"] = predicate

            graph.add_edge(
                source,
                target,
                key=fact_id,
                **attrs,
            )

        instance = cls(
            entity_id=entity_id,
            graph=graph,
        )

        for node_id, attrs in graph.nodes(data=True):
            instance._index_surface_texts(
                node_id,
                attrs.get("surface_texts", []),
            )

        return instance

    def save(
        self,
        conn: sqlite3.Connection,
        overwrite: bool = True,
    ) -> None:
        cursor = conn.cursor()

        if overwrite:
            cursor.execute(
                """
                DELETE FROM entities
                WHERE entity_id = ?
                """,
                (self.entity_id,),
            )

            cursor.execute(
                """
                DELETE FROM facts
                WHERE entity_id = ?
                """,
                (self.entity_id,),
            )

        cursor.executemany(
            """
            INSERT INTO entities(
                entity_id,
                node_id,
                label,
                surface_texts
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                (
                    self.entity_id,
                    node_id,
                    attrs.get("label", ""),
                    json.dumps(
                        attrs.get(
                            "surface_texts",
                            [],
                        )
                    ),
                )
                for node_id, attrs in self.graph.nodes(
                    data=True,
                )
            ),
        )

        cursor.executemany(
            """
            INSERT INTO facts(
                entity_id,
                fact_id,
                source,
                target,
                predicate,
                attributes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    self.entity_id,
                    key,
                    src,
                    dst,
                    attrs.get("predicate", ""),
                    json.dumps(
                        {
                            k: v
                            for k, v in attrs.items()
                            if k != "predicate"
                        }
                    ),
                )
                for src, dst, key, attrs in self.graph.edges(
                    keys=True,
                    data=True,
                )
            ),
        )

        conn.commit()

    @staticmethod
    def init_db(
        conn: sqlite3.Connection,
    ) -> None:
        conn.executescript(
            """
            PRAGMA journal_mode = WAL;
            PRAGMA synchronous = NORMAL;

            CREATE TABLE IF NOT EXISTS entities (
                entity_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                label TEXT NOT NULL,
                surface_texts TEXT NOT NULL,
                PRIMARY KEY(entity_id, node_id)
            );

            CREATE TABLE IF NOT EXISTS facts (
                entity_id TEXT NOT NULL,
                fact_id TEXT NOT NULL,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                predicate TEXT NOT NULL,
                attributes TEXT,
                PRIMARY KEY(entity_id, fact_id)
            );

            CREATE INDEX IF NOT EXISTS idx_entities_entity
            ON entities(entity_id);

            CREATE INDEX IF NOT EXISTS idx_facts_entity
            ON facts(entity_id);

            CREATE INDEX IF NOT EXISTS idx_facts_source
            ON facts(entity_id, source);

            CREATE INDEX IF NOT EXISTS idx_facts_target
            ON facts(entity_id, target);
            """
        )

    def clear(self):
        self.graph.clear()
        
    # ------------------------------------------------------------------
    # Entities
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_surface_text(surface_text: str) -> str:
        return surface_text.lower().strip()

    def _index_surface_texts(
        self,
        entity_id: str,
        surface_texts,
    ) -> None:
        for surface_text in surface_texts:
            key = self._normalize_surface_text(surface_text)

            if key:
                self._surface_text_index[key].add(entity_id)

    def _deindex_surface_texts(
        self,
        entity_id: str,
        surface_texts,
    ) -> None:
        for surface_text in surface_texts:
            key = self._normalize_surface_text(surface_text)

            self._surface_text_index.get(key, set()).discard(entity_id)

    def add_entity(
        self,
        entity_id: str,
        label: str,
        surface_texts=None,
    ) -> None:
        if surface_texts is None:
            surface_texts = []

        self.graph.add_node(
            entity_id,
            label=label,
            surface_texts=list(surface_texts),
        )

        self._index_surface_texts(entity_id, surface_texts)

    def has_entity(
        self,
        entity_id: str,
    ) -> bool:
        return self.graph.has_node(entity_id)

    def get_entity(
        self,
        entity_id: str,
    ):
        if not self.graph.has_node(entity_id):
            return None

        attrs = self.graph.nodes[entity_id]

        return {
            "id": entity_id,
            "label": attrs.get("label", ""),
            "surface_texts": list(
                attrs.get("surface_texts", []),
            ),
        }

    def update_surface_texts(
        self,
        entity_id: str,
        surface_texts,
    ) -> None:
        if not self.graph.has_node(entity_id):
            raise KeyError(entity_id)

        self._deindex_surface_texts(
            entity_id,
            self.graph.nodes[entity_id].get("surface_texts", []),
        )

        self.graph.nodes[entity_id][
            "surface_texts"
        ] = list(surface_texts)

        self._index_surface_texts(entity_id, surface_texts)

    def get_entities_by_surface_text(
        self,
        surface_text: str,
    ):
        """
        Reverse lookup: entities that were trained with this exact
        surface text (case-insensitive, whitespace-trimmed).
        """

        key = self._normalize_surface_text(surface_text)

        return [
            self.get_entity(entity_id)
            for entity_id in self._surface_text_index.get(key, set())
        ]

    def iter_entities(self):
        for entity_id, attrs in self.graph.nodes(
            data=True,
        ):
            yield {
                "id": entity_id,
                "label": attrs.get("label", ""),
                "surface_texts": list(
                    attrs.get("surface_texts", []),
                ),
            }

    # ------------------------------------------------------------------
    # Facts
    # ------------------------------------------------------------------

    def add_fact(
        self,
        source: str,
        target: str,
        predicate: str,
        fact_id: str | None = None,
        **attributes,
    ) -> str:
        if fact_id is None:
            import uuid

            fact_id = str(uuid.uuid4())

        self.graph.add_edge(
            source,
            target,
            key=fact_id,
            predicate=predicate,
            **attributes,
        )

        return fact_id

    def get_fact(
        self,
        fact_id: str,
    ):
        for source, target, key, attrs in self.graph.edges(
            keys=True,
            data=True,
        ):
            if key != fact_id:
                continue

            result = dict(attrs)
            result.update(
                {
                    "id": key,
                    "source": source,
                    "target": target,
                    "predicate": attrs.get(
                        "predicate",
                        "",
                    ),
                }
            )

            return result

        return None

    def iter_facts(self):
        for source, target, key, attrs in self.graph.edges(
            keys=True,
            data=True,
        ):
            result = dict(attrs)

            result.update(
                {
                    "id": key,
                    "source": source,
                    "target": target,
                    "predicate": attrs.get(
                        "predicate",
                        "",
                    ),
                }
            )

            yield result
            
    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def g_json(self):
        return json_graph.node_link_data(
            self.graph,
        )

    def to_json(self):
        return {
            "entity_id": self.entity_id,
            "graph": self.g_json(),
        }