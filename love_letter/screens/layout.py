"""
screens/layout.py
=================
Mixin that builds all tkinter widgets for the GameScreen.

All methods here run ONCE at startup via _build().
They create widgets and store references on `self` so the refresh
and action layers can read/update them later.

Nothing here touches game state — it's purely widget construction.
"""
import tkinter as tk
from ..constants import (FONT_HEADER, FONT_BODY, FONT_SMALL,
                         BG, FG, ACCENT, PANEL, PANEL2, BORDER, GOLD, MUTED)


class LayoutMixin:

    def _build(self):
        """Top-level builder — called once in GameScreen.__init__."""
        self._build_topbar()
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=10, pady=6)
        self._build_sidebar(main)
        self._build_center(main)
        self._build_log(main)
        self._build_bottombar()

    # ── Top bar ──────────────────────────────────────────────────────────────

    def _build_topbar(self):
        top = tk.Frame(self, bg=PANEL, pady=6)
        top.pack(fill="x")
        tk.Label(top, text="♥ Love Letter", font=("Georgia", 18, "bold italic"),
                 bg=PANEL, fg=ACCENT).pack(side="left", padx=16)
        self.round_lbl = tk.Label(top, text="", font=FONT_BODY, bg=PANEL, fg=MUTED)
        self.round_lbl.pack(side="left", padx=10)
        tk.Button(top, text="New Game", font=FONT_SMALL, bg=PANEL2, fg=MUTED,
                  activebackground=ACCENT, activeforeground=BG,
                  bd=0, padx=10, pady=4, cursor="hand2",
                  command=self.on_new_game).pack(side="right", padx=10)

    # ── Left sidebar ─────────────────────────────────────────────────────────

    def _build_sidebar(self, parent):
        """One status card per player: name, tokens, turn status, discards."""
        left = tk.Frame(parent, bg=PANEL, width=180,
                        highlightbackground=BORDER, highlightthickness=1)
        left.pack(side="left", fill="y", padx=(0, 8), pady=4)
        left.pack_propagate(False)
        tk.Label(left, text="Players", font=FONT_HEADER,
                 bg=PANEL, fg=ACCENT).pack(pady=(10, 4))

        self.player_frames = {}
        for p in self.game.players:
            f = tk.Frame(left, bg=PANEL2, pady=4,
                         highlightbackground=BORDER, highlightthickness=1)
            f.pack(fill="x", padx=6, pady=3)
            lbls = {
                "name":    tk.Label(f, text=p.name, font=FONT_BODY,  bg=PANEL2, fg=FG),
                "tokens":  tk.Label(f, text="",      font=FONT_SMALL, bg=PANEL2, fg=GOLD),
                "status":  tk.Label(f, text="",      font=FONT_SMALL, bg=PANEL2, fg=MUTED),
                "discard": tk.Label(f, text="",      font=FONT_SMALL, bg=PANEL2, fg=MUTED,
                                    wraplength=160, justify="left"),
            }
            for lbl in lbls.values():
                lbl.pack(anchor="w", padx=8)
            lbls["discard"].pack(pady=(0, 4))
            self.player_frames[p.name] = {"frame": f, **lbls}

    # ── Centre column ────────────────────────────────────────────────────────

    def _build_center(self, parent):
        """Turn label at the top; everything else floats vertically centred."""
        center = tk.Frame(parent, bg=BG)
        center.pack(side="left", fill="both", expand=True)

        self.turn_lbl = tk.Label(center, text="", font=FONT_HEADER, bg=BG, fg=ACCENT)
        self.turn_lbl.pack(pady=(8, 2))

        # `inner` is placed at 50% / 50% so it stays centred as the window resizes
        mid   = tk.Frame(center, bg=BG)
        mid.pack(fill="both", expand=True)
        inner = tk.Frame(mid, bg=BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        self._build_hand_area(inner)
        self._build_desc_panel(inner)
        self._build_action_row(inner)

    def _build_hand_area(self, parent):
        """Panel that holds the face-up or face-down card widgets."""
        hf = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        hf.pack(fill="x", padx=4, pady=(0, 10))
        tk.Label(hf, text="Your Hand", font=FONT_SMALL,
                 bg=PANEL, fg=MUTED).pack(anchor="w", padx=8, pady=(6, 2))
        self.hand_canvas = tk.Frame(hf, bg=PANEL)
        self.hand_canvas.pack(pady=(0, 10))

    def _build_desc_panel(self, parent):
        """Shows the selected card's name and rule text."""
        df = tk.Frame(parent, bg=PANEL2, highlightbackground=BORDER, highlightthickness=1)
        df.pack(fill="x", padx=4, pady=(0, 8))
        self.card_name_lbl = tk.Label(df, text="", font=FONT_HEADER, bg=PANEL2, fg=ACCENT)
        self.card_name_lbl.pack(pady=(8, 2))
        self.card_desc_lbl = tk.Label(df, text="Select a card to see its effect.",
                                      font=FONT_BODY, bg=PANEL2, fg=MUTED,
                                      wraplength=440, justify="center")
        self.card_desc_lbl.pack(pady=(0, 10), padx=16)

    def _build_action_row(self, parent):
        """Reveal / Play / Next buttons plus the target and guard-guess dropdowns.

        reveal_btn and play_btn live in a shared btn_swap frame so they always
        occupy the same slot — swapping via pack_forget/pack never changes their
        position in the layout, avoiding the clip-off-screen bug that occurs when
        inner uses place() with a fixed size.
        """
        # ── Stable swap frame: exactly one of reveal_btn / play_btn is visible ──
        self.btn_swap = tk.Frame(parent, bg=BG)
        self.btn_swap.pack(pady=4)

        self.reveal_btn = tk.Button(
            self.btn_swap, text="👁  Show My Hand", font=FONT_HEADER,
            bg=PANEL2, fg=FG, activebackground=ACCENT, activeforeground=BG,
            bd=0, padx=24, pady=10, cursor="hand2", command=self._reveal_hand)
        self.reveal_btn.pack()   # visible first (hand starts hidden)

        self.play_btn = tk.Button(
            self.btn_swap, text="Play Card  ♥", font=FONT_HEADER,
            bg=ACCENT, fg=BG, activebackground=GOLD, activeforeground=BG,
            bd=0, padx=24, pady=10, cursor="hand2", command=self._on_play)
        # play_btn starts hidden; _reveal_hand swaps them
        self.play_btn.pack_forget()

        # Target + Guard-guess dropdowns side by side
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=4)
        self.target_var  = tk.StringVar()
        self.guess_var   = tk.StringVar()
        self.target_menu = self._dropdown(row, "Target Player", self.target_var, width=12)
        self.guess_menu  = self._dropdown(row, "Guard Guess",   self.guess_var,  width=16)

        # Result label — shows the outcome of the last card played
        self.result_lbl = tk.Label(parent, text="", font=FONT_BODY, bg=PANEL,
                                   fg=GOLD, wraplength=480, pady=8, padx=12)
        self.result_lbl.pack(fill="x", padx=4)

        # Next Turn button — appears after a card is played, hidden otherwise
        self.next_btn = tk.Button(
            parent, text="Next Turn →", font=FONT_BODY,
            bg=PANEL2, fg=FG, activebackground=ACCENT, activeforeground=BG,
            bd=0, padx=20, pady=7, cursor="hand2", command=self._next_turn)
        self.next_btn.pack(pady=4)
        self.next_btn.pack_forget()

    def _dropdown(self, parent, label: str, var: tk.StringVar, width: int) -> tk.OptionMenu:
        """Create a themed LabelFrame + OptionMenu pair and return the menu widget."""
        box = tk.LabelFrame(parent, text=label, font=FONT_SMALL, bg=BG, fg=MUTED,
                            labelanchor="n", padx=8, pady=6)
        box.pack(side="left", fill="both", expand=True, padx=4)
        menu = tk.OptionMenu(box, var, "")
        menu.config(font=FONT_BODY, bg=PANEL2, fg=FG,
                    activebackground=ACCENT, bd=0, pady=4, width=width)
        menu["menu"].config(bg=PANEL2, fg=FG, font=FONT_BODY)
        menu.pack()
        return menu

    # ── Right log panel ──────────────────────────────────────────────────────

    def _build_log(self, parent):
        """Scrollable text box showing the last 60 game events."""
        right = tk.Frame(parent, bg=PANEL, width=210,
                         highlightbackground=BORDER, highlightthickness=1)
        right.pack(side="right", fill="y", padx=(8, 0), pady=4)
        right.pack_propagate(False)
        tk.Label(right, text="Game Log", font=FONT_HEADER,
                 bg=PANEL, fg=ACCENT).pack(pady=(10, 4))
        self.log_text = tk.Text(right, bg=PANEL2, fg=FG, font=FONT_SMALL,
                                wrap="word", state="disabled", bd=0,
                                width=26, padx=6, pady=4)
        sb = tk.Scrollbar(right, command=self.log_text.yview, bg=PANEL)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)

    # ── Bottom status bar ────────────────────────────────────────────────────

    def _build_bottombar(self):
        bot = tk.Frame(self, bg=PANEL, pady=4)
        bot.pack(fill="x", side="bottom")
        self.deck_lbl   = tk.Label(bot, text="", font=FONT_SMALL, bg=PANEL, fg=MUTED)
        self.tokens_bar = tk.Label(bot, text="", font=FONT_SMALL, bg=PANEL, fg=GOLD)
        self.deck_lbl.pack(side="left",  padx=16)
        self.tokens_bar.pack(side="right", padx=16)