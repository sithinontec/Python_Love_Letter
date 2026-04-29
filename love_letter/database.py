"""
database.py
===========
SQLite storage layer for Love Letter.

Schema
------
sessions   — one row per game session (group of rounds)
rounds     — one row per round inside a session
round_players — per-player stats for each round (tokens earned, eliminated, etc.)
events     — timestamped play-by-play log for every round

Public API (used by game.py)
----------------------------
GameDB(path)                       — open / create the database
db.start_session(player_names)     — returns session_id
db.start_round(session_id, round_num)  — returns round_id
db.log_event(round_id, message)    — insert one play-by-play line
db.end_round(round_id, winner, survivors, player_stats)
db.end_session(session_id, winner, duration_seconds, player_final_tokens)

Query helpers (for stats / history screens)
-------------------------------------------
db.get_all_sessions()
db.get_session_rounds(session_id)
db.get_round_events(round_id)
db.get_player_stats(player_name)
db.get_leaderboard()
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ── Schema DDL ───────────────────────────────────────────────────────────────

_DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT    NOT NULL,
    ended_at        TEXT,
    player_names    TEXT    NOT NULL,   -- comma-separated
    winner          TEXT,
    duration_secs   INTEGER,
    total_rounds    INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS rounds (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES sessions(id),
    round_num   INTEGER NOT NULL,
    started_at  TEXT    NOT NULL,
    ended_at    TEXT,
    winner      TEXT,
    survivors   TEXT    -- comma-separated names still alive at round end
);

CREATE TABLE IF NOT EXISTS round_players (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id        INTEGER NOT NULL REFERENCES rounds(id),
    player_name     TEXT    NOT NULL,
    tokens_earned   INTEGER DEFAULT 0,  -- 1 if won this round, else 0
    was_eliminated  INTEGER DEFAULT 0   -- 1 = TRUE
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id    INTEGER NOT NULL REFERENCES rounds(id),
    occurred_at TEXT    NOT NULL,
    message     TEXT    NOT NULL
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_rounds_session   ON rounds(session_id);
CREATE INDEX IF NOT EXISTS idx_events_round     ON events(round_id);
CREATE INDEX IF NOT EXISTS idx_rp_round         ON round_players(round_id);
CREATE INDEX IF NOT EXISTS idx_rp_player        ON round_players(player_name);
"""


# ─────────────────────────────────────────────────────────────────────────────

class GameDB:
    """Thin wrapper around an SQLite connection for Love Letter logging."""

    def __init__(self, path: Optional[str] = None):
        """
        Open (or create) the SQLite database.

        Parameters
        ----------
        path : str or None
            File path for the .db file.  Defaults to  ../love_letter.db
            relative to this module's directory so it sits at the project root.
        """
        if path is None:
            path = str(Path(__file__).parent.parent / "love_letter.db")

        self._path = path
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row   # columns accessible by name
        self._apply_schema()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _apply_schema(self) -> None:
        self._conn.executescript(_DDL)
        self._conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Write API (called by game.py) ─────────────────────────────────────────

    def start_session(self, player_names: List[str]) -> int:
        """
        Record a new game session.  Returns the new session_id.
        """
        cur = self._conn.execute(
            "INSERT INTO sessions (started_at, player_names) VALUES (?, ?)",
            (self._now(), ", ".join(player_names)),
        )
        self._conn.commit()
        return cur.lastrowid

    def start_round(self, session_id: int, round_num: int) -> int:
        """
        Record a new round inside a session.  Returns the new round_id.
        """
        cur = self._conn.execute(
            "INSERT INTO rounds (session_id, round_num, started_at) VALUES (?, ?, ?)",
            (session_id, round_num, self._now()),
        )
        self._conn.commit()
        return cur.lastrowid

    def log_event(self, round_id: int, message: str) -> None:
        """Insert one play-by-play event line."""
        self._conn.execute(
            "INSERT INTO events (round_id, occurred_at, message) VALUES (?, ?, ?)",
            (round_id, self._now(), message),
        )
        self._conn.commit()

    def end_round(
        self,
        round_id:     int,
        winner:       str,
        survivors:    List[str],
        player_stats: Dict[str, Dict],  # {name: {tokens_earned, eliminated}}
    ) -> None:
        """
        Close a round: set winner / survivors, insert per-player stats.

        player_stats example:
            {
              "Alice": {"tokens_earned": 1, "eliminated": False},
              "Bob":   {"tokens_earned": 0, "eliminated": True},
            }
        """
        self._conn.execute(
            "UPDATE rounds SET ended_at=?, winner=?, survivors=? WHERE id=?",
            (self._now(), winner, ", ".join(survivors), round_id),
        )
        for name, stats in player_stats.items():
            self._conn.execute(
                """INSERT INTO round_players
                       (round_id, player_name, tokens_earned, was_eliminated)
                   VALUES (?, ?, ?, ?)""",
                (
                    round_id,
                    name,
                    stats.get("tokens_earned", 0),
                    1 if stats.get("eliminated", False) else 0,
                ),
            )
        self._conn.commit()

    def end_session(
        self,
        session_id:          int,
        winner:              str,
        duration_seconds:    int,
        player_final_tokens: Dict[str, int],  # {name: token_count}
        total_rounds:        int,
    ) -> None:
        """Close the session row."""
        self._conn.execute(
            """UPDATE sessions
               SET ended_at=?, winner=?, duration_secs=?, total_rounds=?
               WHERE id=?""",
            (self._now(), winner, duration_seconds, total_rounds, session_id),
        )
        self._conn.commit()

    def close(self) -> None:
        """Flush and close the connection."""
        self._conn.close()

    # ── Query API (for history / stats screens) ───────────────────────────────

    def get_all_sessions(self) -> List[sqlite3.Row]:
        """Return all sessions newest-first."""
        return self._conn.execute(
            "SELECT * FROM sessions ORDER BY id DESC"
        ).fetchall()

    def get_session_rounds(self, session_id: int) -> List[sqlite3.Row]:
        """Return all rounds for a given session, in order."""
        return self._conn.execute(
            "SELECT * FROM rounds WHERE session_id=? ORDER BY round_num",
            (session_id,),
        ).fetchall()

    def get_round_events(self, round_id: int) -> List[sqlite3.Row]:
        """Return all play-by-play events for a round in chronological order."""
        return self._conn.execute(
            "SELECT * FROM events WHERE round_id=? ORDER BY id",
            (round_id,),
        ).fetchall()

    def get_player_stats(self, player_name: str) -> Dict:
        """
        Aggregate lifetime stats for one player across all sessions.

        Returns a dict with keys:
            games_played, games_won, rounds_played, rounds_won,
            times_eliminated, win_rate (0.0–1.0)
        """
        row = self._conn.execute(
            """SELECT
                COUNT(DISTINCT s.id)                              AS games_played,
                COUNT(DISTINCT CASE WHEN s.winner=? THEN s.id END) AS games_won,
                COUNT(rp.id)                                      AS rounds_played,
                SUM(rp.tokens_earned)                             AS rounds_won,
                SUM(rp.was_eliminated)                            AS times_eliminated
               FROM sessions s
               JOIN rounds r       ON r.session_id = s.id
               JOIN round_players rp ON rp.round_id = r.id
               WHERE rp.player_name = ?""",
            (player_name, player_name),
        ).fetchone()

        games_played = row["games_played"] or 0
        games_won    = row["games_won"]    or 0
        return {
            "player_name":      player_name,
            "games_played":     games_played,
            "games_won":        games_won,
            "rounds_played":    row["rounds_played"]    or 0,
            "rounds_won":       row["rounds_won"]       or 0,
            "times_eliminated": row["times_eliminated"] or 0,
            "win_rate":         games_won / games_played if games_played else 0.0,
        }

    def get_leaderboard(self) -> List[Dict]:
        """
        Return all players ranked by games won desc, then games played asc.
        Each entry is a dict (same keys as get_player_stats).
        """
        names_row = self._conn.execute(
            """SELECT DISTINCT player_name FROM round_players ORDER BY player_name"""
        ).fetchall()
        results = [self.get_player_stats(r["player_name"]) for r in names_row]
        results.sort(key=lambda d: (-d["games_won"], d["games_played"]))
        return results

    def get_recent_sessions(self, limit: int = 10) -> List[sqlite3.Row]:
        """Return the most recent N sessions."""
        return self._conn.execute(
            "SELECT * FROM sessions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

    def get_incomplete_sessions(self, limit: int = 10) -> List[sqlite3.Row]:
        """
        Return sessions that were never finished (ended_at IS NULL),
        newest-first.  These are candidates for 'Continue Game'.
        """
        return self._conn.execute(
            "SELECT * FROM sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

    def get_session_token_totals(self, session_id: int) -> Dict[str, int]:
        """
        Reconstruct each player's current token count for an in-progress
        session by summing tokens_earned across all completed rounds.
        Returns {player_name: token_count}.
        """
        rows = self._conn.execute(
            """SELECT rp.player_name, SUM(rp.tokens_earned) AS tokens
               FROM round_players rp
               JOIN rounds r ON r.id = rp.round_id
               WHERE r.session_id = ?
               GROUP BY rp.player_name""",
            (session_id,),
        ).fetchall()
        return {r["player_name"]: r["tokens"] for r in rows}

    def get_latest_round_num(self, session_id: int) -> int:
        """Return the highest round_num recorded for a session (0 if none)."""
        row = self._conn.execute(
            "SELECT MAX(round_num) AS mx FROM rounds WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return row["mx"] or 0

    def abandon_session(self, session_id: int) -> None:
        """
        Mark a session as abandoned so it no longer appears in Continue.
        Sets ended_at to now and winner to 'abandoned'.
        """
        self._conn.execute(
            "UPDATE sessions SET ended_at=?, winner='abandoned' WHERE id=?",
            (self._now(), session_id),
        )
        self._conn.commit()