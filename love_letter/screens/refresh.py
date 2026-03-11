"""
screens/refresh.py
==================
Mixin that keeps all visible widgets in sync with the game state.

These methods are called repeatedly throughout a round — never at
startup. They read from `self.game` and write to widgets created
by LayoutMixin. No widgets are created here.

Separation of concerns:
  LayoutMixin  → creates widgets  (runs once)
  RefreshMixin → updates widgets  (runs often)
  GameScreen   → handles actions  (runs on user input)
"""
import tkinter as tk
from ..constants import (CARD_DATA,
                         BG, FG, ACCENT, PANEL, PANEL2, BORDER,
                         RED, GREEN, GOLD, MUTED, FONT_SMALL, FONT_BODY, FONT_HEADER)
from ..models import Player
from ..widgets import CardWidget


class RefreshMixin:

    # ── Full refresh ──────────────────────────────────────────────────────────

    def _refresh(self):
        """
        Full redraw — sync every visible widget with the current game state.
        Called at round start, after next_turn(), and after round resets.
        """
        g   = self.game
        cur = g.current_player

        # Top bar + bottom bar
        self.round_lbl.configure(
            text=f"Round {g.round_num}  |  First to {g.win_tokens} tokens wins")
        self.deck_lbl.configure(text=f"Deck: {len(g.deck)} cards remaining")
        self.tokens_bar.configure(text=self._token_str())
        self.turn_lbl.configure(text=f"Current Turn: {cur.name}")

        # Description panel hint (differs based on whether hand is visible)
        hint = (f"Pass the screen to {cur.name}, then press 'Show My Hand'."
                if self._hand_hidden else "Select a card to see its effect.")
        self.card_name_lbl.configure(text="")
        self.card_desc_lbl.configure(text=hint, fg=MUTED)

        self._refresh_sidebar(cur)
        self._refresh_hand(cur)
        self._update_targets()
        self._update_guesses()
        self._update_log()

    def _token_str(self) -> str:
        """Build the compact token display shown in the bottom bar."""
        g = self.game
        return "  ".join(
            f"{p.name}: {'♥' * p.tokens}{'·' * (g.win_tokens - p.tokens)}"
            for p in g.players)

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _refresh_sidebar(self, cur: Player):
        """Update each player's status card in the left sidebar."""
        g = self.game
        for p in g.players:
            ww = self.player_frames[p.name]

            # Choose colours / text based on player state
            if p.eliminated:
                bg, name_fg      = "#1a0808", "#666"
                status, st_fg    = "✗ Eliminated", RED
            elif p is cur:
                bg, name_fg      = "#3d2a00", GOLD
                status           = "▶ Active turn" + (" 🛡" if p.protected else "")
                st_fg            = GOLD
            else:
                bg, name_fg      = PANEL2, FG
                status           = "🛡 Protected" if p.protected else ""
                st_fg            = GREEN if p.protected else MUTED

            ww["frame"].configure(bg=bg)
            ww["name"].configure(fg=name_fg, bg=bg)
            ww["status"].configure(text=status, fg=st_fg, bg=bg)
            ww["tokens"].configure(
                text=f"♥ {p.tokens} token{'s' if p.tokens != 1 else ''}", bg=bg)
            discard = ", ".join(CARD_DATA[c]["name"] for c in p.discard) or "—"
            ww["discard"].configure(text=f"Discarded: {discard}", bg=bg)

    # ── Hand ──────────────────────────────────────────────────────────────────

    def _refresh_hand(self, cur: Player):
        """Redraw the hand area with real cards (face-up) or backs (face-down)."""
        for w in self.hand_canvas.winfo_children():
            w.destroy()
        if self._hand_hidden:
            for _ in cur.hand:
                self._card_back(self.hand_canvas).pack(side="left", padx=8)
        else:
            for cid in cur.hand:
                cw = CardWidget(self.hand_canvas, cid, width=95, height=135, clickable=True)
                cw.pack(side="left", padx=8)
                cw.bind("<Button-1>", lambda e, c=cid, w=cw: self._select_card(c, w))

    def _card_back(self, parent, w=95, h=135) -> tk.Canvas:
        """Draw a face-down card: purple back with a repeating heart pattern and '?'."""
        c   = tk.Canvas(parent, width=w, height=h, bg=BG, highlightthickness=0)
        pts = lambda x1,y1,x2,y2,r: [
            x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r,
            x2,y2,   x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
        c.create_rectangle(4, 4, w, h, fill="#000", outline="")
        c.create_polygon(pts(2,2,w-2,h-2,10), smooth=True,
                         fill="#2a1a2e", outline=ACCENT, width=2)
        c.create_polygon(pts(6,6,w-6,h-6,7),  smooth=True,
                         fill="",       outline="#8B5E3C", width=1)
        for row in range(3):
            for col in range(3):
                c.create_text(18+col*26, 28+row*30, text="♥",
                              font=("Georgia", 11), fill="#4a2a4a")
        c.create_text(w//2, h//2+10, text="?",
                      font=("Georgia", 32, "bold"), fill="#8B5E3C")
        return c

    def _select_card(self, card_id: int, widget: CardWidget):
        """Highlight the chosen card and populate the description panel."""
        for w in self.hand_canvas.winfo_children():
            if isinstance(w, CardWidget):
                w.set_selected(False)
        self.selected_card = card_id
        widget.set_selected(True)
        self.card_name_lbl.configure(
            text=f"{CARD_DATA[card_id]['value']}  —  {CARD_DATA[card_id]['name']}")
        self.card_desc_lbl.configure(text=CARD_DATA[card_id]["desc"], fg=FG)
        self._update_targets()
        self._update_guesses()

    # ── Dropdowns ─────────────────────────────────────────────────────────────

    def _update_targets(self):
        """
        Populate the Target dropdown with legal choices for the selected card.
        Disabled when no card is selected or when the hand is still hidden.
        """
        g, cur, cid = self.game, self.game.current_player, self.selected_card
        menu = self.target_menu["menu"]
        menu.delete(0, "end")
        self.target_var.set("")

        needs = (not self._hand_hidden) and bool(cid) and (cid in (1, 2, 3, 5, 6))
        self.target_menu.configure(state="normal" if needs else "disabled")
        if not needs:
            return

        first = None
        for p in g.players:
            if p is cur and cid != 5:          continue  # can't target yourself (except Prince)
            if p.eliminated:                   continue
            if p.protected and p is not cur:   continue
            menu.add_command(label=p.name, command=lambda n=p.name: self.target_var.set(n))
            first = first or p.name
        if first:
            self.target_var.set(first)

    def _update_guesses(self):
        """
        Populate the Guard-guess dropdown.
        Only active when the Guard (card 1) is selected.
        """
        menu = self.guess_menu["menu"]
        menu.delete(0, "end")
        self.guess_var.set("")
        if self.selected_card != 1 or self._hand_hidden:
            self.guess_menu.configure(state="disabled")
            return
        self.guess_menu.configure(state="normal")
        for cid in range(2, 9):
            lbl = f"{cid} – {CARD_DATA[cid]['name']}"
            menu.add_command(label=lbl,
                             command=lambda l=lbl, c=cid: (
                                 self.guess_var.set(l),
                                 setattr(self, "_guard_guess", c)))
        self.guess_var.set(f"2 – {CARD_DATA[2]['name']}")
        self._guard_guess = 2

    # ── Log ───────────────────────────────────────────────────────────────────

    def _update_log(self):
        """Rewrite the log panel from the game's event list (last 60 entries)."""
        self.log_text.configure(state="normal")
        self.log_text.delete(1.0, "end")
        for line in self.game.log[-60:]:
            self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
