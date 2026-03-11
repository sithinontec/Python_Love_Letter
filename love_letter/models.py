"""
models.py
=========
Data model for a single player.
Uses a dataclass so Python auto-generates __init__, __repr__, etc.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class Player:
    name: str
    hand:      List[int] = field(default_factory=list)   # cards currently held
    discard:   List[int] = field(default_factory=list)   # cards played this round
    protected: bool = False   # True after playing Handmaid
    eliminated: bool = False  # True when knocked out of the round
    tokens: int = 0           # tokens of affection won across rounds