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

        # NEW: probability tracking
        self.prob_matrix: Dict[str, Dict[str, float]] = {}
        self.envelope_probs: Dict[str, float] = {}

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

        # Init probability structures
        self.prob_matrix = {p: {ck: 0.0 for ck in self.matrix}
                            for p in players}
        self.envelope_probs = {
            ck: 1.0 / len(category_cards(self.category_of_key(ck)))
            for ck in self.matrix
        }

        self._propagate()

    def category_of_key(self, ck: str) -> CardType:
        for cat in ("Suspect", "Weapon", "Room"):
            if ck in [card_key(c) for c in category_cards(cat)]:
                return cat
        raise ValueError(f"Unknown card key {ck}")

    def note_has_card(self, player: str, card: Card) -> None:
        ck = card_key(card)
        for h in self.matrix[ck]:
            self.matrix[ck][h] = (h == player)
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
        cks = [card_key(c) for c in cards]
        unknowns = [ck for ck in cks if self.matrix[ck][player] is None]
        if not unknowns:
            return
        bump = 1.0 / len(unknowns)
        for ck in unknowns:
            self.prob_matrix[player][ck] += bump
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
        return self.matrix.get(card_key(card), {}).get(player)

    def has_been_refuted_before(self, card: Card) -> bool:
        return card_key(card) in self.refuted_cards

    def update_probabilities(self) -> None:
        for ck, holders in self.matrix.items():
            # If someone definitively has it
            definite_holder = next(
                (p for p, v in holders.items() if v is True and p != ENVELOPE), None)
            if definite_holder:
                for p in self.players:
                    self.prob_matrix[p][ck] = 1.0 if p == definite_holder else 0.0
                self.envelope_probs[ck] = 0.0
                continue

            # If it's confirmed in envelope
            if holders[ENVELOPE] is True:
                for p in self.players:
                    self.prob_matrix[p][ck] = 0.0
                self.envelope_probs[ck] = 1.0
                continue

            # If marked false everywhere but envelope
            if all(v is False or h == ENVELOPE for h, v in holders.items()):
                self.envelope_probs[ck] = 1.0
                for p in self.players:
                    self.prob_matrix[p][ck] = 0.0
                continue

            # Distribute evenly
            unknown_players = [p for p in self.players if holders[p] is None]
            env_unknown = holders[ENVELOPE] is None
            slots = len(unknown_players) + (1 if env_unknown else 0)
            if slots > 0:
                share = 1.0 / slots
                for p in self.players:
                    self.prob_matrix[p][ck] = share if p in unknown_players else 0.0
                self.envelope_probs[ck] = share if env_unknown else 0.0

    def _propagate(self) -> None:
        # Card exclusivity
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

        # Category-level
        for cat in ("Suspect", "Weapon", "Room"):
            cks = [card_key(c) for c in category_cards(cat)]
            candidates = [ck for ck in cks if self.matrix[ck]
                          [ENVELOPE] is not False]
            if len(candidates) == 1:
                self.matrix[candidates[0]][ENVELOPE] = True
                for ck in cks:
                    if ck != candidates[0] and self.matrix[ck][ENVELOPE] is None:
                        self.matrix[ck][ENVELOPE] = False

        # Update probabilities at the end
        self.update_probabilities()
