from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from typing import Dict, Type

from smart_slugify import slugify


@dataclass(slots=True)
class RegexRule:
    pattern: str
    compiled: re.Pattern = field(init=False, repr=False)

    def __post_init__(self):
        self.compiled = re.compile(
            self.pattern,
            re.IGNORECASE,
        )


@dataclass
class RegexModel:
    regex_id: str
    rules: Dict[str, list[RegexRule]] = field(
        default_factory=dict,
    )

    @staticmethod
    def make_id(name: str) -> str:
        return f"regex::{slugify(name)}"

    @classmethod
    def create(
        cls: Type["RegexModel"],
        regex_id: str,
    ) -> "RegexModel":
        return cls(regex_id=regex_id)

    @classmethod
    def load(
        cls: Type["RegexModel"],
        conn: sqlite3.Connection,
        regex_id: str,
    ) -> "RegexModel":
        model = cls(regex_id=regex_id)

        cursor = conn.execute(
            """
            SELECT rule_name, pattern
            FROM regex_rules
            WHERE regex_id = ?
            """,
            (regex_id,),
        )

        for rule_name, pattern in cursor:
            try:
                model.add_rule(
                    rule_name,
                    pattern,
                )
            except re.error:
                continue

        return model

    def save(
        self,
        conn: sqlite3.Connection,
        overwrite: bool = True,
    ) -> None:
        cursor = conn.cursor()

        if overwrite:
            cursor.execute(
                """
                DELETE
                FROM regex_rules
                WHERE regex_id = ?
                """,
                (self.regex_id,),
            )

        rows = [
            (
                self.regex_id,
                rule_name,
                rule.pattern,
            )
            for rule_name, rules in self.rules.items()
            for rule in rules
        ]

        if rows:
            cursor.executemany(
                """
                INSERT INTO regex_rules(
                    regex_id,
                    rule_name,
                    pattern
                )
                VALUES (?, ?, ?)
                """,
                rows,
            )

        conn.commit()

    @staticmethod
    def init_db(
        conn: sqlite3.Connection,
    ) -> None:
        conn.executescript("""
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;

        CREATE TABLE IF NOT EXISTS regex_rules (
            regex_id TEXT NOT NULL,
            rule_name TEXT NOT NULL,
            pattern TEXT NOT NULL,
            PRIMARY KEY (
                regex_id,
                rule_name,
                pattern
            )
        );

        CREATE INDEX IF NOT EXISTS idx_regex_rules
        ON regex_rules(regex_id, rule_name);
        """)

    def add_rule(
        self,
        rule_name: str,
        pattern: str,
    ) -> None:
        self.rules.setdefault(
            rule_name,
            [],
        ).append(
            RegexRule(pattern)
        )

    def remove_rule(
        self,
        rule_name: str,
    ) -> None:
        self.rules.pop(
            rule_name,
            None,
        )

    def remove_pattern(
        self,
        rule_name: str,
        pattern: str,
    ) -> None:
        rules = self.rules.get(rule_name)

        if rules is None:
            raise KeyError(rule_name)

        for i, rule in enumerate(rules):
            if rule.pattern == pattern:
                rules.pop(i)
                break
        else:
            raise ValueError(pattern)

        if not rules:
            self.rules.pop(rule_name, None)

    def clear(self) -> None:
        self.rules.clear()

    def to_dict(self):
        return {
            rule_name: [
                rule.pattern
                for rule in rules
            ]
            for rule_name, rules in self.rules.items()
        }