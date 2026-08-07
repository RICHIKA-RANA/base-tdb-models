import json
import sqlite3
from dataclasses import dataclass
from typing import Type
from smart_slugify import slugify


@dataclass
class DictionaryModel:
    dictionary_id: str
    conn: sqlite3.Connection

    @staticmethod
    def make_id(name: str) -> str:
        return f"dictionary::{slugify(name)}"

    @classmethod
    def create(
        cls: Type["DictionaryModel"],
        conn: sqlite3.Connection,
        dictionary_id: str,
    ) -> "DictionaryModel":
        return cls(
            dictionary_id=dictionary_id,
            conn=conn,
        )

    @staticmethod
    def init_db(conn: sqlite3.Connection) -> None:
        conn.executescript("""
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;

        CREATE TABLE IF NOT EXISTS metadata (
            dictionary_id TEXT NOT NULL,
            key           TEXT NOT NULL,
            value         TEXT NOT NULL,
            PRIMARY KEY(dictionary_id, key)
        );

        CREATE TABLE IF NOT EXISTS words (
            dictionary_id TEXT NOT NULL,
            word          TEXT NOT NULL,
            frequency     INTEGER NOT NULL,
            suggestions   TEXT NOT NULL,
            PRIMARY KEY(dictionary_id, word)
        );

        CREATE TABLE IF NOT EXISTS deletes (
            dictionary_id TEXT NOT NULL,
            delete_word   TEXT NOT NULL,
            real_word     TEXT NOT NULL,
            PRIMARY KEY(dictionary_id, delete_word, real_word)
        );

        CREATE INDEX IF NOT EXISTS idx_deletes_lookup
        ON deletes(dictionary_id, delete_word);
        """)

    # ------------------------------------------------------------------
    # metadata
    # ------------------------------------------------------------------

    def set_metadata(self, key: str, value) -> None:
        self.conn.execute(
            """
            INSERT INTO metadata(dictionary_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(dictionary_id, key)
            DO UPDATE SET value = excluded.value
            """,
            (
                self.dictionary_id,
                key,
                json.dumps(value),
            ),
        )

    def get_metadata(self, key: str, default=None):
        row = self.conn.execute(
            """
            SELECT value
            FROM metadata
            WHERE dictionary_id = ?
              AND key = ?
            """,
            (
                self.dictionary_id,
                key,
            ),
        ).fetchone()

        if row is None:
            return default

        return json.loads(row["value"])

    # ------------------------------------------------------------------
    # words
    # ------------------------------------------------------------------

    def has_word(self, word: str) -> bool:
        return (
            self.conn.execute(
                """
                SELECT 1
                FROM words
                WHERE dictionary_id = ?
                  AND word = ?
                """,
                (
                    self.dictionary_id,
                    word,
                ),
            ).fetchone()
            is not None
        )

    def get_frequency(self, word: str) -> int:
        row = self.conn.execute(
            """
            SELECT frequency
            FROM words
            WHERE dictionary_id = ?
              AND word = ?
            """,
            (
                self.dictionary_id,
                word,
            ),
        ).fetchone()

        return 0 if row is None else row["frequency"]

    def insert_word(self, word: str) -> None:
        self.conn.execute(
            """
            INSERT INTO words(
                dictionary_id,
                word,
                frequency,
                suggestions
            )
            VALUES (?, ?, 1, '[]')
            """,
            (
                self.dictionary_id,
                word,
            ),
        )

    def increment_frequency(self, word: str) -> None:
        self.conn.execute(
            """
            UPDATE words
            SET frequency = frequency + 1
            WHERE dictionary_id = ?
              AND word = ?
            """,
            (
                self.dictionary_id,
                word,
            ),
        )

    def word_count(self) -> int:
        row = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM words
            WHERE dictionary_id = ?
              AND frequency > 0
            """,
            (self.dictionary_id,),
        ).fetchone()

        return row[0]

    # ------------------------------------------------------------------
    # suggestions
    # ------------------------------------------------------------------

    def get_suggestions(self, word: str) -> list[str]:
        row = self.conn.execute(
            """
            SELECT suggestions
            FROM words
            WHERE dictionary_id = ?
              AND word = ?
            """,
            (
                self.dictionary_id,
                word,
            ),
        ).fetchone()

        if row is None:
            return []

        return json.loads(row["suggestions"])

    def add_suggestion(
        self,
        delete_word: str,
        real_word: str,
    ) -> None:
        row = self.conn.execute(
            """
            SELECT suggestions
            FROM words
            WHERE dictionary_id = ?
              AND word = ?
            """,
            (
                self.dictionary_id,
                delete_word,
            ),
        ).fetchone()

        if row is None:
            self.conn.execute(
                """
                INSERT INTO words(
                    dictionary_id,
                    word,
                    frequency,
                    suggestions
                )
                VALUES (?, ?, 0, ?)
                """,
                (
                    self.dictionary_id,
                    delete_word,
                    json.dumps([real_word]),
                ),
            )
            return

        suggestions = json.loads(row["suggestions"])

        if real_word not in suggestions:
            suggestions.append(real_word)

            self.conn.execute(
                """
                UPDATE words
                SET suggestions = ?
                WHERE dictionary_id = ?
                  AND word = ?
                """,
                (
                    json.dumps(suggestions),
                    self.dictionary_id,
                    delete_word,
                ),
            )

    # ------------------------------------------------------------------
    # delete mappings
    # ------------------------------------------------------------------

    def add_delete(
        self,
        delete_word: str,
        real_word: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT OR IGNORE INTO deletes(
                dictionary_id,
                delete_word,
                real_word
            )
            VALUES (?, ?, ?)
            """,
            (
                self.dictionary_id,
                delete_word,
                real_word,
            ),
        )

    def get_delete_words(
        self,
        delete_word: str,
    ) -> list[str]:
        rows = self.conn.execute(
            """
            SELECT real_word
            FROM deletes
            WHERE dictionary_id = ?
              AND delete_word = ?
            """,
            (
                self.dictionary_id,
                delete_word,
            ),
        ).fetchall()

        return [row["real_word"] for row in rows]