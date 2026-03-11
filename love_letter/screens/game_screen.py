"""
screens/game_screen.py
======================
Thin orchestrator that composes LayoutMixin + RefreshMixin into a
complete gameplay screen.

Responsibilities here:
  • __init__  : set state variables, call build + refresh
  • Actions   : _reveal_hand, _on_play, _resolve_target, _next_turn
  • Popups    : _priest_reveal, _show_round_end, _start_next_round

Everything else lives in:
  layout.py   → widget construction  (LayoutMixin)
  refresh.py  → widget updates       (RefreshMixin)
"""
import tkinter as tk
from typing import Callable, Optional

from ..constants import (CARD_DATA, FONT_TITLE, FONT_HEADER, FONT_BODY, FONT_SMALL,
                         BG, FG, ACCENT, PANEL, PANEL2, BORDER, RED, GOLD, MUTED)
from ..game import LoveLetterGame
from ..models import Player
from ..widgets import CardWidget
from .layout  import LayoutMixin
from .refresh import RefreshMixin


class GameScreen(LayoutMixin, RefreshMixin, tk.Frame):
    """
    Main gameplay screen shown during every round.

    Inherits widget-building from LayoutMixin and state-sync from
    RefreshMixin. This class only handles user actions and popups.
    """

    def __init__(self, master, game: LoveLetterGame, on_new_game: Callable[[], None]):
        tk.Frame.__init__(self, master, bg=BG)
        self.game         = game
        self.on_new_game  = on_new_game
        self.selected_card: Optional[int] = None
        self._guard_guess = 2     # which card the Guard will guess (default: Priest)
        self._hand_hidden = True  # True → show card backs until player presses "Show My Hand"
        self._build()    # LayoutMixin
        self._refresh()  # RefreshMixin

    # ═══════════════════════════════════════════════════════════════════════
    # ACTIONS
    # ═══════════════════════════════════════════════════════════════════════

    def _reveal_hand(self):
        """Player confirmed it's their turn — flip cards face-up."""
        self._hand_hidden = False
        # Swap within btn_swap so position in inner frame never changes
        self.reveal_btn.pack_forget()
        self.play_btn.pack()
        self._refresh_hand(self.game.current_player)
        self._update_targets()
        self._update_guesses()
        self.card_name_lbl.configure(text="")
        self.card_desc_lbl.configure(text="Select a card to see its effect.", fg=MUTED)

    def _on_play(self):
        """Validate the player's selection, send it to the engine, show the result."""
        g = self.game
        if not self.selected_card:
            self.result_lbl.configure(text="Please select a card first.", fg=RED)
            return

        cid    = self.selected_card
        target = self._resolve_target(cid)
        if target == "NEED_TARGET":
            return  # _resolve_target already showed the prompt

        # Countess rule: must discard Countess if holding King or Prince
        cur = g.current_player
        if cid != 7 and 7 in cur.hand and (5 in cur.hand or 6 in cur.hand):
            self.result_lbl.configure(
                text="You must play the Countess when holding the King or Prince!", fg=RED)
            return

        msg = g.play_card(cid, target, self._guard_guess if cid == 1 else 0)
        self.selected_card = None
        self._guard_guess  = 2
        self.result_lbl.configure(text=msg, fg=GOLD)
        self._update_log()

        if g.round_over or g.game_over:
            # Refresh sidebar + token bar BEFORE opening the popup so totals are current
            self._refresh_sidebar(g.current_player)
            self.tokens_bar.configure(text=self._token_str())
            self._show_round_end()
        else:
            # Hide Play Card, show Next Turn in its place
            self.play_btn.pack_forget()
            self.next_btn.pack(pady=4)
            if cid == 2 and target and not target.protected and "peeks" in msg:
                self._priest_reveal(target)  # Priest: show target's card in a popup
            else:
                self._refresh_sidebar(g.current_player)

    def _resolve_target(self, cid: int):
        """
        Work out who the card targets.
        Returns a Player, None (no target needed/available), or "NEED_TARGET".
        "NEED_TARGET" means we blocked the play and already showed an error message.
        """
        g = self.game
        if cid not in (1, 2, 3, 5, 6):
            return None  # Handmaid, Countess, Princess — no target needed

        if cid == 5 and not self.target_var.get():
            return g.current_player  # Prince with no selection → target self

        valid = [p for p in g.players
                 if p is not g.current_player and not p.eliminated and not p.protected]

        if cid in (1, 2, 3, 6) and not valid:
            return None  # everyone is protected → card fizzles (this is legal)

        tname = self.target_var.get()
        if not tname:
            # Prompt the player to pick someone before pressing Play
            self.result_lbl.configure(
                text="⚠  Please choose a target player first, then press Play Card.", fg=RED)
            self.target_menu.configure(highlightbackground=RED, highlightthickness=2)
            self.after(1500, lambda: self.target_menu.configure(
                highlightbackground=BORDER, highlightthickness=1))
            return "NEED_TARGET"

        return next((p for p in g.players if p.name == tname), None)

    def _next_turn(self):
        """Commit the turn, hide the hand, advance the engine, refresh for next player."""
        self.next_btn.pack_forget()
        self.result_lbl.configure(text="")
        self.selected_card = None
        self.game.next_turn()
        self._hand_hidden = True
        self._refresh()
        # Swap back: hide Play Card, show Show My Hand (both live in btn_swap)
        self.play_btn.pack_forget()
        self.reveal_btn.pack()

    # ═══════════════════════════════════════════════════════════════════════
    # POPUPS
    # ═══════════════════════════════════════════════════════════════════════

    def _priest_reveal(self, target: Player):
        """Small modal showing the target's card after a Priest is played."""
        pop = tk.Toplevel(self)
        pop.title("Priest Reveal")
        pop.configure(bg=PANEL)
        pop.resizable(False, False)
        pop.grab_set()
        tk.Label(pop, text=f"You peek at {target.name}'s hand:",
                 font=FONT_HEADER, bg=PANEL, fg=FG).pack(pady=(20, 10), padx=24)
        if target.hand:
            CardWidget(pop, target.hand[0], width=100, height=145).pack(pady=10)
            tk.Label(pop, text=CARD_DATA[target.hand[0]]["desc"],
                     font=FONT_SMALL, bg=PANEL, fg=MUTED, wraplength=240).pack(padx=20)
        tk.Button(pop, text="Close", font=FONT_BODY, bg=ACCENT, fg=BG,
                  bd=0, padx=20, pady=6, cursor="hand2",
                  command=pop.destroy).pack(pady=16)

    def _show_round_end(self):
        """Modal showing round/game winner, remaining hands, and token totals."""
        g   = self.game
        pop = tk.Toplevel(self)
        pop.title("Round Over")
        pop.configure(bg=BG)
        pop.resizable(False, False)
        pop.grab_set()
        # Height scales with player count so the button is never pushed off-screen
        pop_h = 420 + len(g.players) * 30
        pop.geometry(f"480x{pop_h}")

        # Header
        if g.game_over:
            tk.Label(pop, text="🏆 Game Over!",          font=FONT_TITLE,  bg=BG, fg=GOLD).pack(pady=(24,6))
            tk.Label(pop, text=f"{g.winner.name} wins!", font=FONT_HEADER, bg=BG, fg=FG).pack()
        else:
            tk.Label(pop, text=f"Round {g.round_num-1} Over",              font=FONT_TITLE,  bg=BG, fg=ACCENT).pack(pady=(24,6))
            tk.Label(pop, text=f"♥  {g.round_winner.name} wins this round!", font=FONT_HEADER, bg=BG, fg=FG).pack()

        # Remaining hands (shown at round end when deck runs out or all but one eliminated)
        active = g.active_players()
        if active:
            tk.Label(pop, text="Remaining hands:", font=FONT_BODY, bg=BG, fg=MUTED).pack(pady=(14,4))
            row = tk.Frame(pop, bg=BG)
            row.pack()
            for pl in active:
                col = tk.Frame(row, bg=BG)
                col.pack(side="left", padx=10)
                tk.Label(col, text=pl.name, font=FONT_SMALL, bg=BG, fg=FG).pack()
                if pl.hand:
                    CardWidget(col, pl.hand[0], width=70, height=100).pack()

        # Token totals
        tk.Label(pop, text="Token Totals:", font=FONT_BODY, bg=BG, fg=MUTED).pack(pady=(12,2))
        for pl in g.players:
            tk.Label(pop, font=FONT_BODY, bg=BG,
                     fg=GOLD if pl.tokens else FG,
                     text=f"  {pl.name}: {'♥'*pl.tokens}  ({pl.tokens}/{g.win_tokens})").pack()

        # Bottom button
        if g.game_over:
            btn_txt = "New Game"
            btn_cmd = lambda: (pop.destroy(), self.on_new_game())
        else:
            btn_txt = "Next Round →"
            btn_cmd = lambda: (pop.destroy(), self._start_next_round())
        tk.Button(pop, text=btn_txt, font=FONT_HEADER, bg=ACCENT, fg=BG,
                  bd=0, padx=20, pady=8, cursor="hand2", command=btn_cmd).pack(pady=16)

    def _start_next_round(self):
        """Reset UI state and hand off to the game engine to start a new round."""
        self.next_btn.pack_forget()
        self.result_lbl.configure(text="")
        self.selected_card = None
        self.game.start_next_round()
        self._hand_hidden = True
        self._refresh()
        # Swap back: hide Play Card, show Show My Hand (both live in btn_swap)
        self.play_btn.pack_forget()
        self.reveal_btn.pack()