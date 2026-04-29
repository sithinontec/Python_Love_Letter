import tkinter as tk
from typing import Dict, List

from .constants import BG
from .database import GameDB
from .game import LoveLetterGame
from .models import Player
from .screens import SetupScreen, GameScreen
from .screens.continue_screen import ContinueScreen


class App(tk.Tk):
    """Root application window. Manages screen transitions."""

    def __init__(self):
        super().__init__()
        self.title("Love Letter")
        self.configure(bg=BG)
        self.geometry("1060x680")
        self.minsize(900, 600)
        self.current_screen: tk.Frame | None = None

        # Shared DB instance — lives for the whole app lifetime
        self._db = GameDB()

        # On launch: show Continue screen if saved games exist, else Setup
        if self._db.get_incomplete_sessions(limit=1):
            self._show_continue()
        else:
            self._show_setup()

    # ── Screen transitions ────────────────────────────────────────────────────

    def _show_continue(self):
        self._swap_screen(
            ContinueScreen(
                self,
                db=self._db,
                on_continue=self._resume_game,
                on_new_game=self._show_setup,
            )
        )

    def _show_setup(self):
        self._swap_screen(SetupScreen(self, self._start_game))

    # ── Game start (brand new) ────────────────────────────────────────────────

    def _start_game(self, names: List[str]):
        game = LoveLetterGame(names, db=self._db)
        game.start_round()
        game.draw_card(game.current_player)
        self._swap_screen(GameScreen(self, game, self._show_setup))

    # ── Game resume (from DB) ─────────────────────────────────────────────────

    def _resume_game(
        self,
        session_id:     int,
        player_names:   List[str],
        token_map:      Dict[str, int],
        next_round_num: int,
    ):
        """
        Reconstruct a LoveLetterGame from the saved session state, then
        re-attach it to the existing DB session so new events continue
        appending to the same session_id.

        What we restore:
          • player names and their token counts (from round_players aggregation)
          • round number (last completed round + 1)
          • win_tokens threshold (derived from player count, same as __init__)

        What we cannot restore (by design — Love Letter rounds are short):
          • the exact cards in each player's hand / the deck state
          • mid-round progress
        So we always resume at the START of the next fresh round.
        """
        game = LoveLetterGame(
            player_names,
            db=self._db,
            resume_session_id=session_id,
            resume_round_num=next_round_num,
        )

        # Restore token counts accumulated in previous rounds
        for player in game.players:
            player.tokens = token_map.get(player.name, 0)

        # Deal the resuming round
        game.start_round()
        game.draw_card(game.current_player)

        self._swap_screen(GameScreen(self, game, self._show_setup))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _swap_screen(self, new_screen: tk.Frame):
        if self.current_screen:
            self.current_screen.destroy()
        new_screen.pack(fill="both", expand=True)
        self.current_screen = new_screen