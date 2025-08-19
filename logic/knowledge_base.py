from typing import Dict, List, Optional, Tuple
from models.cards import Card, CardType, category_cards, card_key

ENVELOPE = "ENVELOPE"


class KnowledgeBase:
    def __init__(self, owner: str):
        self.owner = owner
        self.players: List[str] = []
        # matrix[card_key][holder] -> True/False/None (None = unknown)
        self.matrix: Dict[str, Dict[str, Optional[bool]]] = {}
        # Track cards that have been revealed/refuted at least once
        self.refuted_cards: set[str] = set()

    def initialize(self, players: List[str], all_cards: List[Card], my_hand: List[Card]) -> None:
        self.players = players[:]
        holders = players + [ENVELOPE]
        for c in all_cards:
            ck = card_key(c)
            self.matrix[ck] = {h: None for h in holders}

        # Our hand is known
        for c in my_hand:
            ck = card_key(c)
            for h in holders:
                self.matrix[ck][h] = (h == self.owner)

        # A card cannot be both in someone's hand and the envelope
        for c in all_cards:
            ck = card_key(c)
            if self.matrix[ck][self.owner]:
                self.matrix[ck][ENVELOPE] = False

        self._propagate()

    def note_has_card(self, player: str, card: Card) -> None:
        ck = card_key(card)
        for h in self.matrix[ck]:
            self.matrix[ck][h] = (h == player)
        # Mark this card as refuted — it has been shown at least once
        self.refuted_cards.add(ck)
        self._propagate()

    def note_cannot_have_any(self, player: str, cards: List[Card]) -> None:
        for c in cards:
            ck = card_key(c)
            if player in self.matrix[ck]:
                if self.matrix[ck][player] is not True:
                    self.matrix[ck][player] = False
        self._propagate()

    def note_has_one_of(self, player: str, cards: List[Card]) -> None:
        # Placeholder for future deduction logic
        self._propagate()

    def is_card_resolved(self, card: Card) -> bool:
        ck = card_key(card)
        vals = self.matrix.get(ck, {})
        return list(vals.values()).count(True) == 1

    def holder_of(self, card: Card) -> Optional[str]:
        ck = card_key(card)
        for h, v in self.matrix.get(ck, {}).items():
            if v is True:
                return h
        return None

    def possible_in_envelope(self, cat: CardType) -> List[Card]:
        res = []
        for c in category_cards(cat):
            ck = card_key(c)
            v = self.matrix.get(ck, {}).get(ENVELOPE, None)
            if v is not False and self.holder_of(c) is None:
                res.append(c)
        return res

    def confirmed_solution(self) -> Optional[Tuple[Card, Card, Card]]:
        suspects = [c for c in category_cards(
            "Suspect") if self.matrix[card_key(c)][ENVELOPE] is True]
        weapons = [c for c in category_cards(
            "Weapon") if self.matrix[card_key(c)][ENVELOPE] is True]
        rooms = [c for c in category_cards(
            "Room") if self.matrix[card_key(c)][ENVELOPE] is True]
        if len(suspects) == 1 and len(weapons) == 1 and len(rooms) == 1:
            return suspects[0], weapons[0], rooms[0]
        return None

    def current_solution_guess(self) -> Optional[Tuple[Card, Card, Card]]:
        def single(cats: CardType):
            cand = self.possible_in_envelope(cats)
            return cand[0] if len(cand) == 1 else None
        s, w, r = single("Suspect"), single("Weapon"), single("Room")
        if s and w and r:
            return (s, w, r)
        return None

    def is_known_to_player(self, player: str, card: Card) -> Optional[bool]:
        """Return True if player is known to have the card, False if known not to, None if unknown."""
        return self.matrix.get(card_key(card), {}).get(player)

    def has_been_refuted_before(self, card: Card) -> bool:
        """Return True if this card has been revealed/refuted at least once before."""
        return card_key(card) in self.refuted_cards

    def _propagate(self) -> None:
        # Card exclusivity: only one holder per card
        for ck, row in self.matrix.items():
            trues = [h for h, v in row.items() if v is True]
            if len(trues) == 1:
                for h in row:
                    if h != trues[0]:
                        row[h] = False
            falses = [h for h, v in row.items() if v is False]
            if len(falses) == len(row) - 1:
                for h in row:
                    if row[h] is None:
                        row[h] = True

        # Category-level: exactly one of each category in envelope
        for cat in ("Suspect", "Weapon", "Room"):
            cks = [card_key(c) for c in category_cards(cat)]
            candidates = [ck for ck in cks if self.matrix[ck]
                          [ENVELOPE] is not False]
            if len(candidates) == 1:
                self.matrix[candidates[0]][ENVELOPE] = True
                for ck in cks:
                    if ck != candidates[0] and self.matrix[ck][ENVELOPE] is None:
                        self.matrix[ck][ENVELOPE] = False
