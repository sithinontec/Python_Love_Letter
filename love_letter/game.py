"""
game.py
=======
Pure-Python game engine — no GUI code here.

Flow each round:
  1. start_round()       — shuffle deck, deal one card to each player
  2. draw_card(player)   — player draws their second card to start their turn
  3. play_card(...)      — player plays one card; engine resolves its effect
  4. next_turn()         — advance to next living player
  5. Repeat 2-4 until one player remains or deck runs out
  6. _end_round()        — award a token; check for game winner
"""
import random
from typing import List, Optional

from .constants import CARD_DATA, WIN_TOKENS
from .models import Player


class LoveLetterGame:

    def __init__(self, player_names: List[str]):
        self.players     = [Player(n) for n in player_names]
        self.deck:       List[int] = []
        self.set_aside:  Optional[int] = None   # one card removed from play each round
        self.extra_aside: List[int] = []         # 3 extra cards removed in 2-player games
        self.current_idx = 0
        self.round_num   = 1
        self.log:        List[str] = []
        self.win_tokens  = WIN_TOKENS.get(len(self.players), 4)
        self.round_over  = False
        self.game_over   = False
        self.winner:       Optional[Player] = None
        self.round_winner: Optional[Player] = None

    # ── Deck helpers ────────────────────────────────────────────────────────

    def build_deck(self) -> List[int]:
        """Return a freshly shuffled deck (card IDs repeated by count)."""
        deck = [cid for cid, info in CARD_DATA.items()
                for _ in range(info["count"])]
        random.shuffle(deck)
        return deck

    # ── Round lifecycle ─────────────────────────────────────────────────────

    def start_round(self):
        """Reset all player state, build a new deck, and deal opening hands."""
        self.deck = self.build_deck()
        for p in self.players:
            p.hand, p.discard, p.protected, p.eliminated = [], [], False, False

        # One card is always set aside face-down (unknown to everyone)
        self.set_aside = self.deck.pop()

        # 2-player variant: three additional cards are removed face-down
        self.extra_aside = [self.deck.pop() for _ in range(3)] \
                           if len(self.players) == 2 else []

        for p in self.players:
            p.hand.append(self.deck.pop())  # each player starts with one card

        self.round_over  = False
        self.round_winner = None
        self.log = [f"── Round {self.round_num} begins ──"]

    def start_next_round(self):
        """Start a new round; the previous winner goes first."""
        if self.round_winner:
            # Position index just before the winner so next_turn() lands on them
            idx = self.players.index(self.round_winner)
            self.current_idx = (idx - 1) % len(self.players)
        self.start_round()
        # Advance to the first non-eliminated player (the winner)
        self._advance_index()
        self.draw_card(self.current_player)  # draw the turn-start card

    # ── Accessors ───────────────────────────────────────────────────────────

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
        p.protected = False       # protection from Handmaid expires each turn
        self.draw_card(p)
        # Remind the player if the Countess rule forces their hand
        if 7 in p.hand and (5 in p.hand or 6 in p.hand):
            self.log.append(f"{p.name} must discard the Countess (holds King/Prince).")

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

        # Countess rule: if you hold the Countess AND King/Prince, you must play Countess
        if card_id != 7 and 7 in p.hand and (5 in p.hand or 6 in p.hand):
            return "You must play the Countess!"

        p.hand.remove(card_id)
        p.discard.append(card_id)
        msg = self._resolve(card_id, p, target, guess)
        self.log.append(msg)

        # Check if the round should end after this play
        if len(self.active_players()) <= 1 or not self.deck:
            self._end_round()
        return msg

    # ── Card resolution (one method per card) ───────────────────────────────

    def _resolve(self, card_id, player, target, guess) -> str:
        """Dispatch to the correct card handler."""
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
        """Guess a target's card. Correct → target eliminated."""
        if not target or target.protected:
            return f"{player.name} plays Guard — no valid target."
        gname = CARD_DATA[guess]["name"]
        if target.hand and target.hand[0] == guess:
            self._eliminate(target)
            return f"{player.name} plays Guard → {gname} on {target.name}. Correct! {target.name} eliminated!"
        return f"{player.name} plays Guard → {gname} on {target.name}. Wrong."

    def _priest(self, player, target) -> str:
        """Peek at a target's hand (result shown in the GUI)."""
        if not target or target.protected:
            return f"{player.name} plays Priest — no valid target."
        peeked = CARD_DATA[target.hand[0]]["name"] if target.hand else "nothing"
        return f"{player.name} plays Priest → peeks at {target.name}'s hand: {peeked}."

    def _baron(self, player, target) -> str:
        """Compare values; lower card is eliminated."""
        if not target or target.protected:
            return f"{player.name} plays Baron — no valid target."
        mv, tv = (player.hand[0] if player.hand else 0), (target.hand[0] if target.hand else 0)
        if mv > tv:   self._eliminate(target);  return f"{player.name} plays Baron. {target.name}({tv}) eliminated!"
        if tv > mv:   self._eliminate(player);  return f"{player.name} plays Baron. {player.name}({mv}) eliminated!"
        return f"{player.name} plays Baron → tie! Nobody eliminated."

    def _handmaid(self, player) -> str:
        """Grant protection until the player's next turn."""
        player.protected = True
        return f"{player.name} plays Handmaid — protected until next turn."

    def _prince(self, player, target) -> str:
        """Force a player (possibly yourself) to discard and redraw."""
        if not target:
            return f"{player.name} plays Prince — no valid target."
        if target.protected and target is not player:
            return f"{player.name} plays Prince — target is protected."
        old = target.hand[0] if target.hand else None
        if old:
            target.discard.append(old)
            target.hand = []
            if old == 8:          # Princess discarded → eliminated
                self._eliminate(target)
                return f"{player.name} plays Prince on {target.name} — Princess discarded, eliminated!"
            # Draw from deck or use the set-aside card if deck is empty
            if self.deck:         target.hand.append(self.deck.pop())
            elif self.set_aside:  target.hand.append(self.set_aside); self.set_aside = None
        return f"{player.name} plays Prince on {target.name} — {target.name} draws a new card."

    def _king(self, player, target) -> str:
        """Swap hands with another player."""
        if not target or target.protected:
            return f"{player.name} plays King — no valid target."
        player.hand, target.hand = target.hand, player.hand
        return f"{player.name} plays King — trades hands with {target.name}."

    def _princess(self, player) -> str:
        """Playing the Princess eliminates yourself immediately."""
        self._eliminate(player)
        return f"{player.name} plays the Princess and is immediately eliminated!"

    # ── Shared helper ────────────────────────────────────────────────────────

    def _eliminate(self, player: Player):
        """Remove a player from the round and clear their hand."""
        player.eliminated = True
        player.discard.extend(player.hand)
        player.hand = []

    def _advance_index(self):
        """Move current_idx forward to the next non-eliminated player."""
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
        Award a token; check if the game is won.
        """
        self.round_over = True
        active = self.active_players()

        if len(active) == 1:
            self.round_winner = active[0]
        else:
            # Highest hand value wins
            best  = max(p.hand[0] if p.hand else 0 for p in active)
            tied  = [p for p in active if (p.hand[0] if p.hand else 0) == best]
            # Tie-break: most total discard value
            self.round_winner = max(tied, key=lambda p: sum(p.discard))

        self.round_winner.tokens += 1
        self.log.append(
            f"Round over! {self.round_winner.name} wins a token! "
            f"({self.round_winner.tokens}/{self.win_tokens})"
        )
        if self.round_winner.tokens >= self.win_tokens:
            self.game_over = True
            self.winner = self.round_winner
            self.log.append(f"🏆 {self.winner.name} wins the game!")
        else:
            self.round_num += 1