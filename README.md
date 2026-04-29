# ♥ Love Letter — Digital Board Game

A digital recreation of the **Love Letter** card game, built entirely in Python using the standard library.

## Game Overview

Love Letter is a game of risk, deduction, and luck for **2–4 players**. Each round, players draw and play cards to eliminate opponents or deduce their hands. The last player standing — or the player holding the highest card when the deck runs out — wins the round and earns a token of affection. The first player to collect enough tokens wins the game.

### Cards

| Value | Name     | Copies | Effect |
|-------|----------|--------|--------|
| 1     | Guard    | 5      | Name a non-Guard card. If the target holds it, they are eliminated. |
| 2     | Priest   | 2      | Look at another player's hand. |
| 3     | Baron    | 2      | Compare hands with another player. The lower card is eliminated. |
| 4     | Handmaid | 2      | You are protected until your next turn. |
| 5     | Prince   | 2      | Choose any player (including yourself) to discard and redraw. |
| 6     | King     | 1      | Trade hands with another player. |
| 7     | Countess | 1      | Must be discarded if you also hold the King or Prince. |
| 8     | Princess | 1      | If you discard this card, you are immediately eliminated. |

### Winning Conditions

| Players | Tokens needed to win |
|---------|---------------------|
| 2       | 7                   |
| 3       | 5                   |
| 4       | 4                   |

## How to Run from Scratch

### Prerequisites

- **Python 3.10** or higher
- **tkinter** (included with Python on Windows and macOS; on Linux, install via `sudo apt-get install python3-tk`)

This project uses **only Python standard library modules** — no third-party packages are required.

### Step 1 — Clone or download the project

```bash
git clone <repository-url>
cd Python_Love_Letter
```

### Step 2 — Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

> Since this project only uses the standard library, this step will not install any packages. It is included to follow proper Python project conventions.

### Step 4 — Run the game

```bash
python main.py
```

## Project Structure

```
Python_Love_Letter/
├── main.py                  # Entry point — run this file
├── requirements.txt         # Dependencies (stdlib only)
├── love_letter.db           # SQLite database (auto-created on first run)
│
└── love_letter/             # Main package
    ├── __init__.py
    ├── app.py               # Root Tk window, screen transitions
    ├── constants.py         # Card data, UI theme colours, fonts
    ├── database.py          # SQLite storage layer (sessions, rounds, events)
    ├── game.py              # Pure-Python game engine (no GUI code)
    ├── models.py            # Player data model (dataclass)
    ├── widgets.py           # Reusable CardWidget (tkinter Canvas)
    │
    └── screens/             # GUI screens sub-package
        ├── __init__.py
        ├── setup_screen.py      # Player name / count selection
        ├── continue_screen.py   # Resume or abandon saved games
        ├── game_screen.py       # Main gameplay (actions + popups)
        ├── layout.py            # Widget construction mixin
        └── refresh.py           # Widget update / sync mixin
```

## Features

- **Full GUI** — tkinter interface with procedurally-drawn card widgets, colour-coded game log, and popup dialogs for card reveals
- **SQLite database** — all game sessions, rounds, and play-by-play events are persisted automatically
- **Game records** — player statistics, leaderboard, and session history stored in the database
- **Save & resume** — unfinished games can be continued from where you left off
- **Hot-seat multiplayer** — 2–4 players take turns on the same screen
