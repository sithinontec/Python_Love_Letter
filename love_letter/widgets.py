"""
widgets.py
==========
CardWidget — a tkinter Canvas that draws one Love Letter card.

Cards are drawn procedurally:
  • Rounded rectangle body (card colour from CARD_COLORS)
  • Inner border ring
  • Value circle at the top
  • Subtle heart watermark in the centre (colour blended so it doesn't clash)
  • Card name at the bottom above a divider line
"""
import tkinter as tk
from .constants import CARD_DATA, CARD_COLORS, FONT_CARDNUM, BG, ACCENT


class CardWidget(tk.Canvas):

    def __init__(self, master, card_id: int,
                 width: int = 90, height: int = 130,
                 clickable: bool = False, **kw):
        super().__init__(master, width=width, height=height,
                         bg=BG, highlightthickness=0, **kw)
        self.card_id  = card_id
        self.w, self.h = width, height
        self.selected  = False
        self._draw()
        if clickable:
            self.bind("<Enter>", lambda _: self.configure(cursor="hand2"))
            self.bind("<Leave>", lambda _: self.configure(cursor=""))

    # ── Drawing ──────────────────────────────────────────────────────────────

    def _draw(self):
        self.delete("all")
        w, h = self.w, self.h
        bg_c, fg_c = CARD_COLORS.get(self.card_id, ("#333", "#fff"))

        self.create_rectangle(4, 4, w, h, fill="#000", outline="")           # shadow
        self._rrect(2, 2, w-2, h-2, 10, fill=bg_c,                           # card body
                    outline=ACCENT if self.selected else fg_c, width=2)
        self._rrect(6, 6, w-6, h-6, 7, fill="", outline=fg_c, width=1)       # inner border

        # Heart watermark — drawn early so text layers appear on top
        self.create_text(w//2, h//2+6, text="♥", font=("Georgia", 36),
                         fill=self._blend(bg_c, fg_c, 0.25))

        # Value circle + number
        self.create_oval(w//2-16, 8, w//2+16, 40, fill=fg_c, outline="")
        self.create_text(w//2, 24, text=str(self.card_id), font=FONT_CARDNUM, fill=bg_c)

        # Divider + card name
        self.create_line(10, h-38, w-10, h-38, fill=fg_c, width=1)
        self.create_text(w//2, h-22, text=CARD_DATA[self.card_id]["name"],
                         font=("Georgia", 9, "bold"), fill=fg_c,
                         width=w-12, justify="center")

    def _rrect(self, x1, y1, x2, y2, r, **kw):
        """Draw a rounded rectangle as a smooth polygon."""
        pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2,
               x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
        self.create_polygon(pts, smooth=True, **kw)

    @staticmethod
    def _blend(c1: str, c2: str, t: float) -> str:
        """Linear interpolation between two hex colours (t=0→c1, t=1→c2)."""
        r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
        r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
        return "#{:02x}{:02x}{:02x}".format(
            int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t))

    # ── State ────────────────────────────────────────────────────────────────

    def set_selected(self, val: bool):
        """Highlight the card border when selected."""
        self.selected = val
        self._draw()