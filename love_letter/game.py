"""
game.py
=======
Pure-Python game engine — no GUI code here.
Game records are written automatically to game_log.txt with no external calls
required; logging is triggered internally at every state transition.

Flow each round:
  1. start_round()       — shuffle deck, deal one card to each player
  2. draw_card(player)   — player draws their second card to start their turn
  3. play_card(...)      — player plays one card; engine resolves its effect
  4. next_turn()         — advance to next living player
  5. Repeat 2-4 until one player remains or deck runs out
  6. _end_round()        — award a token; check for game winner
"""
import os
import random
from datetime import datetime
from typing import List, Optional

from .constants import CARD_DATA, WIN_TOKENS
from .models import Player


# ── Logging constants ────────────────────────────────────────────────────────

_LOG_FILE  = os.path.join(os.path.dirname(__file__), "..", "game_log.txt")
_SEPARATOR = "=" * 60
_THIN_SEP  = "-" * 60


# ─────────────────────────────────────────────────────────────────────────────

class LoveLetterGame:

    def __init__(self, player_names: List[str]):
        self.players      = [Player(n) for n in player_names]
        self.deck:        List[int] = []
        self.set_aside:   Optional[int] = None
        self.extra_aside: List[int] = []
        self.current_idx  = 0
        self.round_num    = 1
        self.log:         List[str] = []
        self.win_tokens   = WIN_TOKENS.get(len(self.players), 4)
        self.round_over   = False
        self.game_over    = False
        self.winner:       Optional[Player] = None
        self.round_winner: Optional[Player] = None

        # Start logging this session immediately on construction
        self._session_start = datetime.now()
        self._log_session_start(player_names)

    # ── Internal logger helpers ──────────────────────────────────────────────

    @staticmethod
    def _ts() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _append(line: str = "") -> None:
        """Append one line to game_log.txt (creates the file if absent)."""
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _log_session_start(self, player_names: List[str]) -> None:
        self._append(_SEPARATOR)
        self._append(f"SESSION START  {self._ts()}")
        self._append(f"Players : {', '.join(player_names)}")
        self._append(_SEPARATOR)

    def _log_round_start(self) -> None:
        self._append(f"\n  ROUND {self.round_num}  [{self._ts()}]")
        self._append(f"  {_THIN_SEP}")

    def _log_event(self, message: str) -> None:
        self._append(f"  [{self._ts()}]  {message}")

    def _log_round_result(self) -> None:
        survivors = [p.name for p in self.active_players()]
        self._append(f"  >> Round winner : {self.round_winner.name}")
        self._append(f"  >> Survivors    : {', '.join(survivors)}")

    def _log_game_result(self) -> None:
        scores = {p.name: p.tokens for p in self.players}
        self._append(f"\n{_THIN_SEP}")
        self._append(f"GAME OVER  [{self._ts()}]")
        self._append(f"Winner : {self.winner.name}")
        self._append("Scores :")
        for name, tokens in sorted(scores.items(), key=lambda x: -x[1]):
            marker = "  <--" if name == self.winner.name else ""
            self._append(f"  {name:<20} {tokens} token(s){marker}")

    def _log_session_end(self) -> None:
        elapsed = datetime.now() - self._session_start
        mins, secs = divmod(int(elapsed.total_seconds()), 60)
        self._append(f"\nSession duration : {mins}m {secs}s")
        self._append(f"SESSION END    {self._ts()}")
        self._append(_SEPARATOR + "\n")

    # ── Deck helpers ─────────────────────────────────────────────────────────

    def build_deck(self) -> List[int]:
        """Return a freshly shuffled deck (card IDs repeated by count)."""
        deck = [cid for cid, info in CARD_DATA.items()
                for _ in range(info["count"])]
        random.shuffle(deck)
        return deck

    # ── Round lifecycle ──────────────────────────────────────────────────────

    def start_round(self):
        """Reset all player state, build a new deck, and deal opening hands."""
        self.deck = self.build_deck()
        for p in self.players:
            p.hand, p.discard, p.protected, p.eliminated = [], [], False, False

        self.set_aside   = self.deck.pop()
        self.extra_aside = [self.deck.pop() for _ in range(3)] \
                           if len(self.players) == 2 else []

        for p in self.players:
            p.hand.append(self.deck.pop())

        self.round_over   = False
        self.round_winner = None
        self.log = [f"── Round {self.round_num} begins ──"]

        self._log_round_start()                          # ← auto-log

    def start_next_round(self):
        """Start a new round; the previous winner goes first."""
        if self.round_winner:
            idx = self.players.index(self.round_winner)
            self.current_idx = (idx - 1) % len(self.players)
        self.start_round()
        self._advance_index()
        self.draw_card(self.current_player)

    # ── Accessors ────────────────────────────────────────────────────────────

    @property
    def current_player(self) -> Player:
        return self.players[self.current_idx]

    def active_players(self) -> List[Player]:
        return [p for p in self.players if not p.eliminated]

    def draw_card(self, player: Player) -> bool:
        """Draw the top card into a player's hand. Returns False if deck empty."""
        if self.deck:
            player.hand.append(self.deck.pop())
            return True
        return False

    # ── Turn flow ────────────────────────────────────────────────────────────

    def next_turn(self):
        """Advance to the next living player and deal them a card."""
        if len(self.active_players()) <= 1 or not self.deck:
            self._end_round()
            return
        self._advance_index()
        p = self.current_player
        p.protected = False
        self.draw_card(p)
        if 7 in p.hand and (5 in p.hand or 6 in p.hand):
            msg = f"{p.name} must discard the Countess (holds King/Prince)."
            self.log.append(msg)
            self._log_event(msg)                         # ← auto-log

    def play_card(self, card_id: int,
                  target: Optional[Player] = None,
                  guess: int = 0) -> str:
        """
        Play one card from the current player's hand.
        Returns a human-readable result string.
        """
        p = self.current_player
        if card_id not in p.hand:
            return "Card not in hand."

        if card_id != 7 and 7 in p.hand and (5 in p.hand or 6 in p.hand):
            return "You must play the Countess!"

        p.hand.remove(card_id)
        p.discard.append(card_id)
        msg = self._resolve(card_id, p, target, guess)
        self.log.append(msg)
        self._log_event(msg)                             # ← auto-log

        if len(self.active_players()) <= 1 or not self.deck:
            self._end_round()
        return msg

    # ── Card resolution ──────────────────────────────────────────────────────

    def _resolve(self, card_id, player, target, guess) -> str:
        handlers = {
            1: lambda: self._guard(player, target, guess),
            2: lambda: self._priest(player, target),
            3: lambda: self._baron(player, target),
            4: lambda: self._handmaid(player),
            5: lambda: self._prince(player, target),
            6: lambda: self._king(player, target),
            7: lambda: f"{player.name} plays Countess.",
            8: lambda: self._princess(player),
        }
        return handlers[card_id]()

    def _guard(self, player, target, guess) -> str:
        if not target or target.protected:
            return f"{player.name} plays Guard — no valid target."
        gname = CARD_DATA[guess]["name"]
        if target.hand and target.hand[0] == guess:
            self._eliminate(target)
            return f"{player.name} plays Guard → {gname} on {target.name}. Correct! {target.name} eliminated!"
        return f"{player.name} plays Guard → {gname} on {target.name}. Wrong."

    def _priest(self, player, target) -> str:
        if not target or target.protected:
            return f"{player.name} plays Priest — no valid target."
        peeked = CARD_DATA[target.hand[0]]["name"] if target.hand else "nothing"
        return f"{player.name} plays Priest → peeks at {target.name}'s hand: {peeked}."

    def _baron(self, player, target) -> str:
        if not target or target.protected:
            return f"{player.name} plays Baron — no valid target."
        mv, tv = (player.hand[0] if player.hand else 0), (target.hand[0] if target.hand else 0)
        if mv > tv:   self._eliminate(target);  return f"{player.name} plays Baron. {target.name}({tv}) eliminated!"
        if tv > mv:   self._eliminate(player);  return f"{player.name} plays Baron. {player.name}({mv}) eliminated!"
        return f"{player.name} plays Baron → tie! Nobody eliminated."

    def _handmaid(self, player) -> str:
        player.protected = True
        return f"{player.name} plays Handmaid — protected until next turn."

    def _prince(self, player, target) -> str:
        if not target:
            return f"{player.name} plays Prince — no valid target."
        if target.protected and target is not player:
            return f"{player.name} plays Prince — target is protected."
        old = target.hand[0] if target.hand else None
        if old:
            target.discard.append(old)
            target.hand = []
            if old == 8:
                self._eliminate(target)
                return f"{player.name} plays Prince on {target.name} — Princess discarded, eliminated!"
            if self.deck:         target.hand.append(self.deck.pop())
            elif self.set_aside:  target.hand.append(self.set_aside); self.set_aside = None
        return f"{player.name} plays Prince on {target.name} — {target.name} draws a new card."

    def _king(self, player, target) -> str:
        if not target or target.protected:
            return f"{player.name} plays King — no valid target."
        player.hand, target.hand = target.hand, player.hand
        return f"{player.name} plays King — trades hands with {target.name}."

    def _princess(self, player) -> str:
        self._eliminate(player)
        return f"{player.name} plays the Princess and is immediately eliminated!"

    # ── Shared helpers ───────────────────────────────────────────────────────

    def _eliminate(self, player: Player):
        player.eliminated = True
        player.discard.extend(player.hand)
        player.hand = []

    def _advance_index(self):
        while True:
            self.current_idx = (self.current_idx + 1) % len(self.players)
            if not self.players[self.current_idx].eliminated:
                break

    # ── Round end ────────────────────────────────────────────────────────────

    def _end_round(self):
        """
        Determine the round winner:
          1. Last player standing, OR
          2. Highest card value, OR
          3. Highest total discard value (tie-breaker)
        Award a token; check for game winner.
        """
        self.round_over = True
        active = self.active_players()

        if len(active) == 1:
            self.round_winner = active[0]
        else:
            best = max(p.hand[0] if p.hand else 0 for p in active)
            tied = [p for p in active if (p.hand[0] if p.hand else 0) == best]
            self.round_winner = max(tied, key=lambda p: sum(p.discard))

        self.round_winner.tokens += 1
        result_msg = (
            f"Round over! {self.round_winner.name} wins a token! "
            f"({self.round_winner.tokens}/{self.win_tokens})"
        )
        self.log.append(result_msg)
        self._log_round_result()                         # ← auto-log

        if self.round_winner.tokens >= self.win_tokens:
            self.game_over = True
            self.winner    = self.round_winner
            win_msg = f"🏆 {self.winner.name} wins the game!"
            self.log.append(win_msg)
            self._log_game_result()                      # ← auto-log
            self._log_session_end()                      # ← auto-log
        else:
            self.round_num += 1