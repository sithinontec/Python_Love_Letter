"""
screens/game_screen.py
======================
Main gameplay screen — shown during every round.

Layout (left → centre → right):
  • Sidebar  : player list with token counts, status, discards
  • Centre   : hand cards, card description, action controls
  • Log panel: scrolling history of moves

Card hiding:
  Cards are shown face-down until the active player presses "Show My Hand",
  so passing the device between players is safe.
"""
import tkinter as tk
from typing import Callable, Optional

from ..constants import (CARD_DATA, FONT_TITLE, FONT_HEADER, FONT_BODY, FONT_SMALL,
                         BG, FG, ACCENT, PANEL, PANEL2, BORDER, RED, GREEN, GOLD, MUTED)
from ..game import LoveLetterGame
from ..models import Player
from ..widgets import CardWidget


class GameScreen(tk.Frame):

    def __init__(self, master, game: LoveLetterGame, on_new_game: Callable[[], None]):
        super().__init__(master, bg=BG)
        self.game           = game
        self.on_new_game    = on_new_game
        self.selected_card: Optional[int] = None
        self._guard_guess   = 2      # current Guard guess value
        self._hand_hidden   = True   # hide cards until player confirms it's their turn
        self._build()
        self._refresh()

    # ═══════════════════════════════════════════════════════════════════════
    # BUILD  –  construct all widgets once at startup
    # ═══════════════════════════════════════════════════════════════════════

    def _build(self):
        self._build_topbar()
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=10, pady=6)
        self._build_sidebar(main)
        self._build_center(main)
        self._build_log(main)
        self._build_bottombar()

    def _build_topbar(self):
        top = tk.Frame(self, bg=PANEL, pady=6)
        top.pack(fill="x")
        tk.Label(top, text="♥ Love Letter", font=("Georgia",18,"bold italic"),
                 bg=PANEL, fg=ACCENT).pack(side="left", padx=16)
        self.round_lbl = tk.Label(top, text="", font=FONT_BODY, bg=PANEL, fg=MUTED)
        self.round_lbl.pack(side="left", padx=10)
        tk.Button(top, text="New Game", font=FONT_SMALL, bg=PANEL2, fg=MUTED,
                  activebackground=ACCENT, activeforeground=BG,
                  bd=0, padx=10, pady=4, cursor="hand2",
                  command=self.on_new_game).pack(side="right", padx=10)

    def _build_sidebar(self, parent):
        """Left panel: one card per player showing name, tokens, status, discards."""
        left = tk.Frame(parent, bg=PANEL, width=180,
                        highlightbackground=BORDER, highlightthickness=1)
        left.pack(side="left", fill="y", padx=(0,8), pady=4)
        left.pack_propagate(False)
        tk.Label(left, text="Players", font=FONT_HEADER, bg=PANEL, fg=ACCENT).pack(pady=(10,4))

        self.player_frames = {}
        for p in self.game.players:
            f = tk.Frame(left, bg=PANEL2, pady=4,
                         highlightbackground=BORDER, highlightthickness=1)
            f.pack(fill="x", padx=6, pady=3)
            lbls = {
                "name":    tk.Label(f, text=p.name,  font=FONT_BODY,  bg=PANEL2, fg=FG),
                "tokens":  tk.Label(f, text="",       font=FONT_SMALL, bg=PANEL2, fg=GOLD),
                "status":  tk.Label(f, text="",       font=FONT_SMALL, bg=PANEL2, fg=MUTED),
                "discard": tk.Label(f, text="",       font=FONT_SMALL, bg=PANEL2, fg=MUTED,
                                    wraplength=160, justify="left"),
            }
            for lbl in lbls.values():
                lbl.pack(anchor="w", padx=8)
            lbls["discard"].pack(pady=(0,4))
            self.player_frames[p.name] = {"frame": f, **lbls}

    def _build_center(self, parent):
        """Centre column: turn label + vertically-centred inner block."""
        center = tk.Frame(parent, bg=BG)
        center.pack(side="left", fill="both", expand=True)

        self.turn_lbl = tk.Label(center, text="", font=FONT_HEADER, bg=BG, fg=ACCENT)
        self.turn_lbl.pack(pady=(8,2))

        # Use place() on a child frame so it stays centred as the window resizes
        mid = tk.Frame(center, bg=BG)
        mid.pack(fill="both", expand=True)
        inner = tk.Frame(mid, bg=BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        # ── Hand ──────────────────────────────────────────────────────────
        hf = tk.Frame(inner, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        hf.pack(fill="x", padx=4, pady=(0,10))
        tk.Label(hf, text="Your Hand", font=FONT_SMALL, bg=PANEL, fg=MUTED).pack(anchor="w", padx=8, pady=(6,2))
        self.hand_canvas = tk.Frame(hf, bg=PANEL)
        self.hand_canvas.pack(pady=(0,10))

        # ── Card description panel ────────────────────────────────────────
        df = tk.Frame(inner, bg=PANEL2, highlightbackground=BORDER, highlightthickness=1)
        df.pack(fill="x", padx=4, pady=(0,8))
        self.card_name_lbl = tk.Label(df, text="", font=FONT_HEADER, bg=PANEL2, fg=ACCENT)
        self.card_name_lbl.pack(pady=(8,2))
        self.card_desc_lbl = tk.Label(df, text="Select a card to see its effect.",
                                      font=FONT_BODY, bg=PANEL2, fg=MUTED,
                                      wraplength=440, justify="center")
        self.card_desc_lbl.pack(pady=(0,10), padx=16)

        # ── Reveal / Play / Next buttons ──────────────────────────────────
        self.reveal_btn = tk.Button(inner, text="👁  Show My Hand", font=FONT_HEADER,
                                    bg=PANEL2, fg=FG, activebackground=ACCENT, activeforeground=BG,
                                    bd=0, padx=24, pady=10, cursor="hand2",
                                    command=self._reveal_hand)
        self.reveal_btn.pack(pady=4)

        # ── Target + Guard-guess dropdowns ────────────────────────────────
        row = tk.Frame(inner, bg=BG)
        row.pack(fill="x", pady=4)
        self.target_var  = tk.StringVar()
        self.guess_var   = tk.StringVar()
        self.target_menu = self._dropdown(row, "Target Player", self.target_var, width=12)
        self.guess_menu  = self._dropdown(row, "Guard Guess",   self.guess_var,  width=16)

        self.play_btn = tk.Button(inner, text="Play Card  ♥", font=FONT_HEADER,
                                  bg=ACCENT, fg=BG, activebackground=GOLD, activeforeground=BG,
                                  bd=0, padx=24, pady=10, cursor="hand2", command=self._on_play)
        self.play_btn.pack(pady=8)

        self.result_lbl = tk.Label(inner, text="", font=FONT_BODY, bg=PANEL,
                                   fg=GOLD, wraplength=480, pady=8, padx=12)
        self.result_lbl.pack(fill="x", padx=4)

        self.next_btn = tk.Button(inner, text="Next Turn →", font=FONT_BODY,
                                  bg=PANEL2, fg=FG, activebackground=ACCENT, activeforeground=BG,
                                  bd=0, padx=20, pady=7, cursor="hand2", command=self._next_turn)
        self.next_btn.pack(pady=4)
        self.next_btn.pack_forget()   # hidden until after a card is played

        # Dummy label kept so old references don't crash (never displayed)
        self.instruction_lbl = tk.Label(center, text="", bg=BG)

    def _dropdown(self, parent, label: str, var: tk.StringVar, width: int) -> tk.OptionMenu:
        """Helper: create a styled LabelFrame + OptionMenu and return the menu widget."""
        box = tk.LabelFrame(parent, text=label, font=FONT_SMALL, bg=BG, fg=MUTED,
                            labelanchor="n", padx=8, pady=6)
        box.pack(side="left", fill="both", expand=True, padx=4)
        menu = tk.OptionMenu(box, var, "")
        menu.config(font=FONT_BODY, bg=PANEL2, fg=FG,
                    activebackground=ACCENT, bd=0, pady=4, width=width)
        menu["menu"].config(bg=PANEL2, fg=FG, font=FONT_BODY)
        menu.pack()
        return menu

    def _build_log(self, parent):
        """Right panel: scrollable log of every move."""
        right = tk.Frame(parent, bg=PANEL, width=210,
                         highlightbackground=BORDER, highlightthickness=1)
        right.pack(side="right", fill="y", padx=(8,0), pady=4)
        right.pack_propagate(False)
        tk.Label(right, text="Game Log", font=FONT_HEADER, bg=PANEL, fg=ACCENT).pack(pady=(10,4))
        self.log_text = tk.Text(right, bg=PANEL2, fg=FG, font=FONT_SMALL,
                                wrap="word", state="disabled", bd=0, width=26, padx=6, pady=4)
        sb = tk.Scrollbar(right, command=self.log_text.yview, bg=PANEL)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)

    def _build_bottombar(self):
        bot = tk.Frame(self, bg=PANEL, pady=4)
        bot.pack(fill="x", side="bottom")
        self.deck_lbl   = tk.Label(bot, text="", font=FONT_SMALL, bg=PANEL, fg=MUTED)
        self.tokens_bar = tk.Label(bot, text="", font=FONT_SMALL, bg=PANEL, fg=GOLD)
        self.deck_lbl.pack(side="left",  padx=16)
        self.tokens_bar.pack(side="right", padx=16)

    # ═══════════════════════════════════════════════════════════════════════
    # REFRESH  –  sync all visible widgets with game state
    # ═══════════════════════════════════════════════════════════════════════

    def _refresh(self):
        """Full redraw — called at the start of each turn and after round resets."""
        g = self.game
        cur = g.current_player
        self.round_lbl.configure(text=f"Round {g.round_num}  |  First to {g.win_tokens} tokens wins")
        self.deck_lbl.configure(text=f"Deck: {len(g.deck)} cards remaining")
        self.tokens_bar.configure(
            text="  ".join(f"{p.name}: {'♥'*p.tokens}{'·'*(g.win_tokens-p.tokens)}"
                           for p in g.players))
        self.turn_lbl.configure(text=f"Current Turn: {cur.name}")
        # Description panel hint changes depending on whether the hand is visible
        hint = (f"Pass the screen to {cur.name}, then press 'Show My Hand'."
                if self._hand_hidden else "Select a card to see its effect.")
        self.card_name_lbl.configure(text="")
        self.card_desc_lbl.configure(text=hint, fg=MUTED)
        self._refresh_sidebar(cur)
        self._refresh_hand(cur)
        self._update_targets()
        self._update_guesses()
        self._update_log()

    def _refresh_sidebar(self, cur: Player):
        """Update every player card in the left sidebar."""
        g = self.game
        for p in g.players:
            ww = self.player_frames[p.name]
            if p.eliminated:
                bg, name_fg, status = "#1a0808", "#666", "✗ Eliminated"
                status_fg = RED
            elif p is cur:
                bg, name_fg = "#3d2a00", GOLD
                status = "▶ Active turn" + (" 🛡" if p.protected else "")
                status_fg = GOLD
            else:
                bg, name_fg = PANEL2, FG
                status = "🛡 Protected" if p.protected else ""
                status_fg = GREEN if p.protected else MUTED

            ww["frame"].configure(bg=bg)
            ww["name"].configure(fg=name_fg, bg=bg)
            ww["status"].configure(text=status, fg=status_fg, bg=bg)
            ww["tokens"].configure(text=f"♥ {p.tokens} token{'s' if p.tokens!=1 else ''}",
                                   bg=bg)
            discard_txt = "Discarded: " + (
                ", ".join(CARD_DATA[c]["name"] for c in p.discard) or "—")
            ww["discard"].configure(text=discard_txt, bg=bg)

    def _refresh_hand(self, cur: Player):
        """Redraw the hand area with real cards or face-down backs."""
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
        """Draw a face-down card (purple back with heart pattern and '?')."""
        c = tk.Canvas(parent, width=w, height=h, bg=BG, highlightthickness=0)
        pts = lambda x1,y1,x2,y2,r: [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r,
                                       x2,y2, x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
        c.create_rectangle(4, 4, w, h, fill="#000", outline="")
        c.create_polygon(pts(2,2,w-2,h-2,10), smooth=True, fill="#2a1a2e", outline=ACCENT, width=2)
        c.create_polygon(pts(6,6,w-6,h-6,7),  smooth=True, fill="",       outline="#8B5E3C", width=1)
        for row in range(3):
            for col in range(3):
                c.create_text(18+col*26, 28+row*30, text="♥", font=("Georgia",11), fill="#4a2a4a")
        c.create_text(w//2, h//2+10, text="?", font=("Georgia",32,"bold"), fill="#8B5E3C")
        return c

    def _select_card(self, card_id: int, widget: CardWidget):
        """Highlight the chosen card and show its rule in the description panel."""
        for w in self.hand_canvas.winfo_children():
            if isinstance(w, CardWidget): w.set_selected(False)
        self.selected_card = card_id
        widget.set_selected(True)
        self.card_name_lbl.configure(
            text=f"{CARD_DATA[card_id]['value']}  —  {CARD_DATA[card_id]['name']}")
        self.card_desc_lbl.configure(text=CARD_DATA[card_id]['desc'], fg=FG)
        self._update_targets()
        self._update_guesses()

    def _update_targets(self):
        """Populate the Target dropdown with valid choices for the selected card."""
        g   = self.game
        cur = g.current_player
        cid = self.selected_card
        menu = self.target_menu["menu"]
        menu.delete(0, "end")
        self.target_var.set("")
        needs = (not self._hand_hidden) and (cid in (1,2,3,5,6) if cid else False)
        self.target_menu.configure(state="normal" if needs else "disabled")
        if not needs:
            return
        first = None
        for p in g.players:
            if p is cur and cid != 5: continue   # can't target yourself (except Prince)
            if p.eliminated or (p.protected and p is not cur): continue
            menu.add_command(label=p.name, command=lambda n=p.name: self.target_var.set(n))
            first = first or p.name
        if first:
            self.target_var.set(first)

    def _update_guesses(self):
        """Populate the Guard-guess dropdown (only active when Guard is selected)."""
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

    def _update_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete(1.0, "end")
        for line in self.game.log[-60:]:
            self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ═══════════════════════════════════════════════════════════════════════
    # ACTIONS  –  buttons and turn transitions
    # ═══════════════════════════════════════════════════════════════════════

    def _reveal_hand(self):
        """Player has confirmed it's their turn — flip cards face-up."""
        self._hand_hidden = False
        self.reveal_btn.pack_forget()
        self.play_btn.pack(pady=8)
        self._refresh_hand(self.game.current_player)
        self._update_targets()
        self._update_guesses()
        self.card_name_lbl.configure(text="")
        self.card_desc_lbl.configure(text="Select a card to see its effect.", fg=MUTED)

    def _on_play(self):
        """Validate selections, call the game engine, then show the result."""
        g = self.game
        if not self.selected_card:
            self.result_lbl.configure(text="Please select a card first.", fg=RED)
            return

        cid    = self.selected_card
        target = self._resolve_target(cid)
        if target == "NEED_TARGET":
            return   # prompt already shown inside _resolve_target

        # Countess rule enforced in the UI as well as the engine
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
            # Update sidebar/tokens so they reflect the new state BEFORE the popup opens
            self._refresh_sidebar(g.current_player)
            self.tokens_bar.configure(
                text="  ".join(f"{p.name}: {'♥'*p.tokens}{'·'*(g.win_tokens-p.tokens)}"
                               for p in g.players))
            self._show_round_end()
        else:
            self.play_btn.pack_forget()
            self.next_btn.pack(pady=4)
            # Priest peeks show a popup before moving on
            if cid == 2 and target and not target.protected and "peeks" in msg:
                self._priest_reveal(target)
            else:
                self._refresh_sidebar(g.current_player)

    def _resolve_target(self, cid: int):
        """
        Return the chosen target Player, or None if no target is needed/available.
        Returns the string "NEED_TARGET" to signal the player must pick one first.
        """
        g = self.game
        if cid not in (1,2,3,5,6):
            return None
        if cid == 5 and not self.target_var.get():
            return g.current_player   # Prince defaults to self

        valid = [p for p in g.players
                 if p is not g.current_player and not p.eliminated and not p.protected]
        if cid in (1,2,3,6) and not valid:
            return None   # no valid targets → card plays with no effect (legal)

        tname = self.target_var.get()
        if not tname:
            self.result_lbl.configure(
                text="⚠  Please choose a target player first, then press Play Card.", fg=RED)
            self.target_menu.configure(highlightbackground=RED, highlightthickness=2)
            self.after(1500, lambda: self.target_menu.configure(
                highlightbackground=BORDER, highlightthickness=1))
            return "NEED_TARGET"

        return next((p for p in g.players if p.name == tname), None)

    def _next_turn(self):
        """Hide hand, advance the game engine, refresh for the next player."""
        self.next_btn.pack_forget()
        self.result_lbl.configure(text="")
        self.selected_card = None
        self.game.next_turn()
        self._hand_hidden = True
        self._refresh()
        self.play_btn.pack_forget()
        self.reveal_btn.pack(pady=4)

    # ═══════════════════════════════════════════════════════════════════════
    # POPUPS  –  priest peek, round end, next round
    # ═══════════════════════════════════════════════════════════════════════

    def _priest_reveal(self, target: Player):
        """Show a small popup revealing the target's card after a Priest is played."""
        p = tk.Toplevel(self)
        p.title("Priest Reveal")
        p.configure(bg=PANEL)
        p.resizable(False, False)
        p.grab_set()
        tk.Label(p, text=f"You peek at {target.name}'s hand:",
                 font=FONT_HEADER, bg=PANEL, fg=FG).pack(pady=(20,10), padx=24)
        if target.hand:
            CardWidget(p, target.hand[0], width=100, height=145).pack(pady=10)
            tk.Label(p, text=CARD_DATA[target.hand[0]]["desc"],
                     font=FONT_SMALL, bg=PANEL, fg=MUTED, wraplength=240).pack(padx=20)
        tk.Button(p, text="Close", font=FONT_BODY, bg=ACCENT, fg=BG,
                  bd=0, padx=20, pady=6, cursor="hand2",
                  command=p.destroy).pack(pady=16)

    def _show_round_end(self):
        """Popup showing who won, remaining hands, and token totals."""
        g = self.game
        p = tk.Toplevel(self)
        p.title("Round Over")
        p.configure(bg=BG)
        p.resizable(False, False)
        p.grab_set()
        p.geometry("460x400")

        if g.game_over:
            tk.Label(p, text="🏆 Game Over!", font=FONT_TITLE, bg=BG, fg=GOLD).pack(pady=(24,6))
            tk.Label(p, text=f"{g.winner.name} wins the game!", font=FONT_HEADER, bg=BG, fg=FG).pack()
        else:
            tk.Label(p, text=f"Round {g.round_num-1} Over", font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(24,6))
            tk.Label(p, text=f"♥  {g.round_winner.name} wins this round!", font=FONT_HEADER, bg=BG, fg=FG).pack()

        # Show remaining hands
        active = g.active_players()
        if active:
            tk.Label(p, text="Remaining hands:", font=FONT_BODY, bg=BG, fg=MUTED).pack(pady=(14,4))
            row = tk.Frame(p, bg=BG)
            row.pack()
            for pl in active:
                col = tk.Frame(row, bg=BG)
                col.pack(side="left", padx=10)
                tk.Label(col, text=pl.name, font=FONT_SMALL, bg=BG, fg=FG).pack()
                if pl.hand:
                    CardWidget(col, pl.hand[0], width=70, height=100).pack()

        # Token totals
        tk.Label(p, text="Token Totals:", font=FONT_BODY, bg=BG, fg=MUTED).pack(pady=(12,2))
        for pl in g.players:
            tk.Label(p, font=FONT_BODY, bg=BG,
                     fg=GOLD if pl.tokens else FG,
                     text=f"  {pl.name}: {'♥'*pl.tokens}  ({pl.tokens}/{g.win_tokens})").pack()

        action = (lambda: (p.destroy(), self.on_new_game())) if g.game_over \
                 else (lambda: (p.destroy(), self._start_next_round()))
        label = "New Game" if g.game_over else "Next Round →"
        tk.Button(p, text=label, font=FONT_HEADER, bg=ACCENT, fg=BG,
                  bd=0, padx=20, pady=8, cursor="hand2", command=action).pack(pady=16)

    def _start_next_round(self):
        """Reset UI state and begin the next round."""
        self.next_btn.pack_forget()
        self.result_lbl.configure(text="")
        self.selected_card = None
        self.game.start_next_round()
        self._hand_hidden = True
        self._refresh()
        self.play_btn.pack_forget()
        self.reveal_btn.pack(pady=4)