"""
constants.py
============
All static game data and UI theme values used across the project.
Nothing here changes at runtime — it's a single source of truth.
"""

# ── Card definitions ────────────────────────────────────────────────────────
# Each entry: card value → name, how many copies exist, rule description.
CARD_DATA = {
    1: {"name": "Guard",    "count": 5, "value": 1,
        "desc": "Name a non-Guard card. If target holds it, they are eliminated."},
    2: {"name": "Priest",   "count": 2, "value": 2,
        "desc": "Look at another player's hand."},
    3: {"name": "Baron",    "count": 2, "value": 3,
        "desc": "Compare hands with another player. Lower card is eliminated."},
    4: {"name": "Handmaid", "count": 2, "value": 4,
        "desc": "You are protected until your next turn."},
    5: {"name": "Prince",   "count": 2, "value": 5,
        "desc": "Choose any player (including yourself) to discard and redraw."},
    6: {"name": "King",     "count": 1, "value": 6,
        "desc": "Trade hands with another player."},
    7: {"name": "Countess", "count": 1, "value": 7,
        "desc": "Must be discarded if you hold the King or Prince."},
    8: {"name": "Princess", "count": 1, "value": 8,
        "desc": "If you discard this card, you are immediately eliminated."},
}

# Background / foreground colour pair for each card value
CARD_COLORS = {
    1: ("#8B0000", "#FFD700"),  # dark red  / gold
    2: ("#1a237e", "#90CAF9"),  # deep blue / light blue
    3: ("#4a148c", "#CE93D8"),  # purple    / lavender
    4: ("#1B5E20", "#A5D6A7"),  # dark green / mint
    5: ("#E65100", "#FFCC80"),  # orange    / peach
    6: ("#880E4F", "#F48FB1"),  # deep pink / rose
    7: ("#263238", "#B0BEC5"),  # dark slate / silver
    8: ("#B71C1C", "#EF9A9A"),  # crimson   / blush
}

# Tokens needed to win per player count
WIN_TOKENS = {2: 7, 3: 5, 4: 4}

# ── UI theme ────────────────────────────────────────────────────────────────
FONT_TITLE   = ("Georgia", 28, "bold")
FONT_HEADER  = ("Georgia", 14, "bold")
FONT_BODY    = ("Georgia", 11)
FONT_SMALL   = ("Georgia", 9)
FONT_CARDNUM = ("Georgia", 22, "bold")

BG     = "#1a0a0a"   # main background
FG     = "#f5e6d3"   # primary text
ACCENT = "#c9a96e"   # gold accent
PANEL  = "#2d1515"   # panel background
PANEL2 = "#3d2020"   # darker panel / inputs
BORDER = "#8B5E3C"   # border / divider
RED    = "#c0392b"   # error / eliminated
GREEN  = "#27ae60"   # protected status
GOLD   = "#f1c40f"   # win highlight
MUTED  = "#9e7b5a"   # secondary text