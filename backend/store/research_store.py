"""
Postgres-backed store for stock analyses and per-session seed tracking.
Analyses survive reloads; the seed table ensures the analysis is sent to a
chat session only once.
"""

import json
from datetime import datetime

import psycopg

from backend.config import settings
from backend.schemas.stock import StockAnalysis


def _connect() -> psycopg.Connection:
    return psycopg.connect(settings.database_url, autocommit=True)


def setup_tables() -> None:
    """Create store tables if missing. Additive only — never alters existing tables."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research_analyses (
                ticker TEXT PRIMARY KEY,
                analysis JSONB NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_session_seeds (
                session_id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                seeded_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        # version of the analysis last sent to this session; NULL = needs seeding
        conn.execute(
            """
            ALTER TABLE chat_session_seeds
            ADD COLUMN IF NOT EXISTS analysis_updated_at TIMESTAMPTZ
            """
        )


def get_analysis_updated_at(ticker: str) -> datetime | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT updated_at FROM research_analyses WHERE ticker = %s",
            (ticker,),
        ).fetchone()
    return row[0] if row else None


def get_analysis(ticker: str) -> StockAnalysis | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT analysis FROM research_analyses WHERE ticker = %s",
            (ticker,),
        ).fetchone()
    if row is None:
        return None
    return StockAnalysis(**row[0])


def save_analysis(analysis: StockAnalysis) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO research_analyses (ticker, analysis, updated_at)
            VALUES (%s, %s, now())
            ON CONFLICT (ticker)
            DO UPDATE SET analysis = EXCLUDED.analysis, updated_at = now()
            """,
            (analysis.ticker, json.dumps(analysis.model_dump(mode="json"))),
        )


def claim_seed(
    session_id: str, ticker: str, analysis_updated_at: datetime
) -> bool | None:
    """
    Atomically claim the right to seed a session with this analysis version.
    Returns True if this is the session's first seed, False if it is a re-seed
    with a newer analysis, and None if the session already has this version.
    """
    with _connect() as conn:
        row = conn.execute(
            """
            INSERT INTO chat_session_seeds (session_id, ticker, analysis_updated_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (session_id) DO UPDATE
            SET analysis_updated_at = EXCLUDED.analysis_updated_at,
                seeded_at = now()
            WHERE chat_session_seeds.analysis_updated_at IS NULL
               OR chat_session_seeds.analysis_updated_at < EXCLUDED.analysis_updated_at
            RETURNING (xmax = 0) AS is_first
            """,
            (session_id, ticker, analysis_updated_at),
        ).fetchone()
    if row is None:
        return None
    return bool(row[0])


def release_seed(session_id: str) -> None:
    """Undo a claim when the seed message failed, so the next call retries it."""
    with _connect() as conn:
        conn.execute(
            "UPDATE chat_session_seeds SET analysis_updated_at = NULL WHERE session_id = %s",
            (session_id,),
        )
