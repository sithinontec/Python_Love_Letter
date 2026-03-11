"""
screens/setup_screen.py
=======================
Opening screen — choose 2-4 players and enter their names.
Calls on_start(names) when the player presses "Begin the Game".
"""
import tkinter as tk
from typing import Callable, List
from ..constants import (FONT_HEADER, FONT_BODY, FONT_SMALL,
                         BG, FG, ACCENT, PANEL, PANEL2, BORDER, GOLD, MUTED)


class SetupScreen(tk.Frame):

    def __init__(self, master, on_start: Callable[[List[str]], None]):
        super().__init__(master, bg=BG)
        self.on_start = on_start
        self._build()

    def _build(self):
        # Title
        tk.Label(self, text="♥  Love Letter  ♥",
                 font=("Georgia", 36, "bold italic"), bg=BG, fg=ACCENT).pack(pady=(50,5))
        tk.Label(self, text="A game of risk, deduction, and romance",
                 font=("Georgia", 13, "italic"), bg=BG, fg=MUTED).pack(pady=(0,40))

        card = tk.Frame(self, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card.pack(padx=80, pady=10, fill="x")

        # Player count selector (2 / 3 / 4 buttons)
        tk.Label(card, text="Number of Players", font=FONT_HEADER, bg=PANEL, fg=FG).pack(pady=(20,8))
        self.num_var = tk.IntVar(value=2)
        btn_row = tk.Frame(card, bg=PANEL)
        btn_row.pack()
        self.num_btns = []
        for n in range(2, 5):
            b = tk.Button(btn_row, text=str(n), font=FONT_HEADER,
                          bg=PANEL2, fg=FG, activebackground=ACCENT, activeforeground=BG,
                          bd=0, padx=20, pady=8, cursor="hand2",
                          command=lambda x=n: self._set_players(x))
            b.pack(side="left", padx=5, pady=5)
            self.num_btns.append(b)

        # Name entry rows (one per player, hidden/shown based on count)
        tk.Label(card, text="Player Names", font=FONT_HEADER, bg=PANEL, fg=FG).pack(pady=(20,8))
        frame = tk.Frame(card, bg=PANEL)
        frame.pack(padx=30, pady=(0,20))
        self.rows: List[tk.Frame] = []
        for i, default in enumerate(["Alice", "Bob", "Carol", "Dave"]):
            row = tk.Frame(frame, bg=PANEL)
            row.pack(pady=3)
            tk.Label(row, text=f"Player {i+1}:", font=FONT_BODY, bg=PANEL, fg=MUTED,
                     width=9, anchor="e").pack(side="left")
            e = tk.Entry(row, font=FONT_BODY, bg=PANEL2, fg=FG, insertbackground=ACCENT,
                         bd=0, width=16, highlightbackground=BORDER, highlightthickness=1)
            e.insert(0, default)
            e.pack(side="left", padx=5)
            self.rows.append(row)

        self._set_players(2)  # default to 2

        tk.Button(self, text="Begin the Game  →", font=FONT_HEADER,
                  bg=ACCENT, fg=BG, activebackground=GOLD, activeforeground=BG,
                  bd=0, padx=30, pady=12, cursor="hand2",
                  command=self._start).pack(pady=30)

    def _set_players(self, n: int):
        """Highlight the chosen count button and show/hide name rows."""
        self.num_var.set(n)
        for i, b in enumerate(self.num_btns):
            b.configure(bg=ACCENT if i+2==n else PANEL2, fg=BG if i+2==n else FG)
        for i, row in enumerate(self.rows):
            for w in row.winfo_children():
                w.configure(state="normal" if i < n else "disabled")
            row.pack() if i < n else row.pack_forget()

    def _start(self):
        n = self.num_var.get()
        names = [row.winfo_children()[1].get().strip() or f"Player {i+1}"
                 for i, row in enumerate(self.rows[:n])]
        self.on_start(names)