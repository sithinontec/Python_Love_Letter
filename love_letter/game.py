"""
game.py
=======
Pure-Python game engine — no GUI code here.
All game records are written automatically to love_letter.db (SQLite) via
the GameDB class in database.py.  No plain-text log file is used.

Flow each round:
  1. start_round()       — shuffle deck, deal one card to each player
  2. draw_card(player)   — player draws their second card to start their turn
  3. play_card(...)      — player plays one card; engine resolves its effect
  4. next_turn()         — advance to next living player
  5. Repeat 2-4 until one player remains or deck runs out
  6. _end_round()        — award a token; check for game winner
"""
import random
from datetime import datetime
from typing import List, Optional

from .constants import CARD_DATA, WIN_TOKENS
from .database import GameDB
from .models import Player


class LoveLetterGame:

    def __init__(
        self,
        player_names:      List[str],
        db:                Optional[GameDB] = None,
        resume_session_id: Optional[int]   = None,
        resume_round_num:  Optional[int]   = None,
    ):
        """
        Parameters
        ----------
        player_names      : list of str
        db                : GameDB instance. If None a default GameDB() is created.
        resume_session_id : if set, re-attach to this existing DB session
                            instead of creating a new one.
        resume_round_num  : if set, start the round counter here instead of 1.
        """
        self.players      = [Player(n) for n in player_names]
        self.deck:        List[int] = []
        self.set_aside:   Optional[int] = None
        self.extra_aside: List[int] = []
        self.current_idx  = 0
        self.round_num    = resume_round_num if resume_round_num else 1
        self.log:         List[str] = []
        self.win_tokens   = WIN_TOKENS.get(len(self.players), 4)
        self.round_over   = False
        self.game_over    = False
        self.winner:       Optional[Player] = None
        self.round_winner: Optional[Player] = None

        # ── DB wiring ────────────────────────────────────────────────────────
        self._db            = db or GameDB()
        self._round_id:      Optional[int] = None
        self._session_start = datetime.now()

        # Re-use existing session when resuming, otherwise open a new one
        if resume_session_id is not None:
            self._session_id: int = resume_session_id
        else:
            self._session_id = self._db.start_session(player_names)

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

        # Open a DB round record
        self._round_id = self._db.start_round(self._session_id, self.round_num)

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
            self._db.log_event(self._round_id, msg)

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
        self._db.log_event(self._round_id, msg)

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
            return (f"{player.name} plays Guard → {gname} on {target.name}. "
                    f"Correct! {target.name} eliminated!")
        return f"{player.name} plays Guard → {gname} on {target.name}. Wrong."

    def _priest(self, player, target) -> str:
        if not target or target.protected:
            return f"{player.name} plays Priest — no valid target."
        peeked = CARD_DATA[target.hand[0]]["name"] if target.hand else "nothing"
        return f"{player.name} plays Priest → peeks at {target.name}'s hand: {peeked}."

    def _baron(self, player, target) -> str:
        if not target or target.protected:
            return f"{player.name} plays Baron — no valid target."
        mv = player.hand[0] if player.hand else 0
        tv = target.hand[0] if target.hand else 0
        if mv > tv:
            self._eliminate(target)
            return f"{player.name} plays Baron. {target.name}({tv}) eliminated!"
        if tv > mv:
            self._eliminate(player)
            return f"{player.name} plays Baron. {player.name}({mv}) eliminated!"
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
                return (f"{player.name} plays Prince on {target.name} — "
                        f"Princess discarded, eliminated!")
            if self.deck:
                target.hand.append(self.deck.pop())
            elif self.set_aside:
                target.hand.append(self.set_aside)
                self.set_aside = None
        return (f"{player.name} plays Prince on {target.name} — "
                f"{target.name} draws a new card.")

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
        Award a token; persist round result to DB; check for game winner.
        """
        self.round_over = True
        active = self.active_players()

        if len(active) == 1:
            self.round_winner = active[0]
        else:
            best   = max(p.hand[0] if p.hand else 0 for p in active)
            tied   = [p for p in active if (p.hand[0] if p.hand else 0) == best]
            self.round_winner = max(tied, key=lambda p: sum(p.discard))

        self.round_winner.tokens += 1
        result_msg = (
            f"Round over! {self.round_winner.name} wins a token! "
            f"({self.round_winner.tokens}/{self.win_tokens})"
        )
        self.log.append(result_msg)

        # ── Persist round result ─────────────────────────────────────────────
        survivors = [p.name for p in active]
        player_stats = {
            p.name: {
                "tokens_earned": 1 if p is self.round_winner else 0,
                "eliminated":    p.eliminated,
            }
            for p in self.players
        }
        self._db.end_round(
            round_id=self._round_id,
            winner=self.round_winner.name,
            survivors=survivors,
            player_stats=player_stats,
        )

        if self.round_winner.tokens >= self.win_tokens:
            self.game_over = True
            self.winner    = self.round_winner
            win_msg = f"🏆 {self.winner.name} wins the game!"
            self.log.append(win_msg)

            # ── Persist session result ───────────────────────────────────────
            elapsed = datetime.now() - self._session_start
            self._db.end_session(
                session_id=self._session_id,
                winner=self.winner.name,
                duration_seconds=int(elapsed.total_seconds()),
                player_final_tokens={p.name: p.tokens for p in self.players},
                total_rounds=self.round_num,
            )
        else:
            self.round_num += 1