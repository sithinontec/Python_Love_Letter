"""
screens/continue_screen.py
==========================
Launch screen shown when incomplete sessions exist in the database.

Layout
------
  ♥ Love Letter ♥          (title)
  "You have unfinished games…"

  ┌─────────────────────────────────────────────┐
  │  Alice, Bob · Round 3 · Started 2025-04-28  │  [Continue]  [Abandon]
  │  Carol, Dave · Round 1 · Started 2025-04-27 │  [Continue]  [Abandon]
  └─────────────────────────────────────────────┘

  [ New Game → ]

Callbacks
---------
on_continue(session_id, player_names, token_map, next_round_num)
    Called when the player picks a saved game to resume.
    The caller (app.py) is responsible for re-constructing LoveLetterGame
    with the correct state.

on_new_game()
    Called when the player chooses to start fresh instead.
"""

import tkinter as tk
from typing import Callable, Dict, List

from ..constants import (FONT_TITLE, FONT_HEADER, FONT_BODY, FONT_SMALL,
                         BG, FG, ACCENT, PANEL, PANEL2, BORDER, GOLD, MUTED, RED)
from ..database import GameDB


class ContinueScreen(tk.Frame):
    """
    Shown on launch when at least one unfinished session exists.

    Parameters
    ----------
    master      : tk root / parent widget
    db          : open GameDB instance (shared with the rest of the app)
    on_continue : called with (session_id, player_names, token_map, next_round_num)
    on_new_game : called with no arguments — switches to SetupScreen
    """

    def __init__(
        self,
        master,
        db: GameDB,
        on_continue: Callable[[int, List[str], Dict[str, int], int], None],
        on_new_game: Callable[[], None],
    ):
        super().__init__(master, bg=BG)
        self._db          = db
        self._on_continue = on_continue
        self._on_new_game = on_new_game
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        # ── Title ─────────────────────────────────────────────────────────────
        tk.Label(self, text="♥  Love Letter  ♥",
                 font=("Georgia", 36, "bold italic"), bg=BG, fg=ACCENT
                 ).pack(pady=(50, 4))
        tk.Label(self, text="A game of risk, deduction, and romance",
                 font=("Georgia", 13, "italic"), bg=BG, fg=MUTED
                 ).pack(pady=(0, 30))

        # ── Sub-heading ───────────────────────────────────────────────────────
        tk.Label(self, text="You have unfinished games — pick one to continue:",
                 font=FONT_HEADER, bg=BG, fg=FG).pack(pady=(0, 12))

        # ── Scrollable session list ───────────────────────────────────────────
        outer = tk.Frame(self, bg=PANEL, highlightbackground=BORDER,
                         highlightthickness=1)
        outer.pack(padx=100, pady=4, fill="x")

        sessions = self._db.get_incomplete_sessions(limit=10)

        if not sessions:
            # Shouldn't normally appear (app.py guards this), but just in case.
            tk.Label(outer, text="No saved games found.",
                     font=FONT_BODY, bg=PANEL, fg=MUTED).pack(pady=20)
        else:
            for row in sessions:
                self._build_session_row(outer, row)

        # ── New Game button ────────────────────────────────────────────────────
        tk.Button(
            self, text="New Game  →", font=FONT_HEADER,
            bg=PANEL2, fg=FG, activebackground=ACCENT, activeforeground=BG,
            bd=0, padx=30, pady=12, cursor="hand2",
            command=self._on_new_game,
        ).pack(pady=30)

    def _build_session_row(self, parent: tk.Frame, session):
        """Render one saved-game row with Continue + Abandon buttons."""
        session_id   = session["id"]
        player_names = [n.strip() for n in session["player_names"].split(",")]
        started_at   = session["started_at"][:16]          # trim seconds

        # Reconstruct progress from DB
        token_map      = self._db.get_session_token_totals(session_id)
        last_round     = self._db.get_latest_round_num(session_id)
        next_round_num = last_round + 1                    # resume on next round

        # Token summary string e.g. "Alice ♥♥  Bob ♥"
        token_strs = [
            f"{n} {'♥' * token_map.get(n, 0) or '—'}"
            for n in player_names
        ]
        token_summary = "  ·  ".join(token_strs)

        # ── Row frame ─────────────────────────────────────────────────────────
        row_frame = tk.Frame(parent, bg=PANEL,
                             highlightbackground=BORDER, highlightthickness=1)
        row_frame.pack(fill="x", padx=12, pady=6)

        # Left: info block
        info = tk.Frame(row_frame, bg=PANEL)
        info.pack(side="left", fill="x", expand=True, padx=12, pady=10)

        tk.Label(info,
                 text=f"  {', '.join(player_names)}",
                 font=FONT_BODY, bg=PANEL, fg=FG, anchor="w"
                 ).pack(fill="x")
        tk.Label(info,
                 text=f"  Round {next_round_num} next  ·  Started {started_at}",
                 font=FONT_SMALL, bg=PANEL, fg=MUTED, anchor="w"
                 ).pack(fill="x")
        tk.Label(info,
                 text=f"  {token_summary}",
                 font=FONT_SMALL, bg=PANEL, fg=GOLD, anchor="w"
                 ).pack(fill="x")

        # Right: action buttons
        btn_frame = tk.Frame(row_frame, bg=PANEL)
        btn_frame.pack(side="right", padx=12, pady=10)

        tk.Button(
            btn_frame, text="Continue ▶", font=FONT_BODY,
            bg=ACCENT, fg=BG, activebackground=GOLD, activeforeground=BG,
            bd=0, padx=14, pady=6, cursor="hand2",
            command=lambda sid=session_id, names=player_names,
                           tm=token_map, nr=next_round_num:
                self._on_continue(sid, names, tm, nr),
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            btn_frame, text="Abandon ✕", font=FONT_BODY,
            bg=PANEL2, fg=RED, activebackground=RED, activeforeground=BG,
            bd=0, padx=14, pady=6, cursor="hand2",
            command=lambda sid=session_id, rf=row_frame:
                self._abandon(sid, rf),
        ).pack(side="left")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _abandon(self, session_id: int, row_frame: tk.Frame):
        """Mark the session abandoned in the DB and remove its row from the UI."""
        self._db.abandon_session(session_id)
        row_frame.destroy()
